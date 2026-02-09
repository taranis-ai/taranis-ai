import contextlib
import os
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Generator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import redis
import requests
from rq import Queue


def _wait_for_http_ok(url: str, timeout_seconds: int = 20, poll_interval: float = 0.5) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            resp.raise_for_status()
            return
        except Exception as exc:  # pragma: no cover - used for readiness polling
            last_exc = exc
            time.sleep(poll_interval)
    raise RuntimeError(f"Timed out waiting for {url}: {last_exc}")


REPO_ROOT = Path(__file__).resolve().parents[4]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_redis(port: int, password: str, timeout_seconds: int = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    client = redis.Redis(host="127.0.0.1", port=port, password=password)
    while time.monotonic() < deadline:
        try:
            if client.ping():
                return
        except Exception as exc:  # pragma: no cover - readiness polling
            last_exc = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for redis on port {port}: {last_exc}")


@pytest.fixture(scope="session")
def redis_backend() -> Generator[dict[str, str], None, None]:
    env_url = os.getenv("TARANIS_E2E_REDIS_URL")
    env_password = os.getenv("TARANIS_E2E_REDIS_PASSWORD", "supersecret")
    if env_url:
        yield {"url": env_url, "password": env_password}
        return

    password = "supersecret"
    port = _find_free_port()

    docker_bin = shutil.which("docker")
    if docker_bin:
        env = os.environ.copy()
        env["REDIS_PASSWORD"] = password
        env["TARANIS_REDIS_PORT"] = str(port)
        compose_file = REPO_ROOT / "dev" / "compose.yml"
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "redis"],
            check=True,
            env=env,
        )
        _wait_for_redis(port, password)
        try:
            yield {"url": f"redis://localhost:{port}", "password": password}
        finally:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "-v", "--remove-orphans"],
                check=True,
                env=env,
            )
        return

    if redis_server := shutil.which("redis-server"):
        proc = subprocess.Popen(
            [
                redis_server,
                "--port",
                str(port),
                "--requirepass",
                password,
                "--save",
                "",
                "--appendonly",
                "no",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _wait_for_redis(port, password)
        try:
            yield {"url": f"redis://localhost:{port}", "password": password}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - best effort cleanup
                proc.kill()
        return

    pytest.skip("docker and redis-server not available - skipping redis e2e test")


@pytest.fixture(scope="session")
def core_process(redis_backend: dict[str, str]) -> Generator[str, None, None]:
    env = os.environ | {
        "API_KEY": "test_key",
        "JWT_SECRET_KEY": "test_key",
        "REDIS_URL": redis_backend["url"],
        "REDIS_PASSWORD": redis_backend["password"],
        "SQLALCHEMY_DATABASE_URI": "sqlite:////tmp/taranis_ai_e2e.db",
        "PRE_SEED_PASSWORD_ADMIN": "admin",
        "TARANIS_AUTHENTICATOR": "database",
        "DISABLE_SCHEDULER": "true",
        "FLASK_APP": "app.py",
    }
    port = int(env.get("TARANIS_CORE_PORT", "5010"))

    core_path = str(REPO_ROOT / "src" / "core")
    env["PYTHONPATH"] = core_path
    proc = subprocess.Popen(
        ["flask", "run", "--no-reload", "--port", str(port)],
        cwd=core_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{port}/api"
    try:
        _wait_for_http_ok(f"{base_url}/isalive")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - best effort cleanup
            proc.kill()
        with contextlib.suppress(Exception):
            Path("/tmp/taranis_ai_e2e.db").unlink()


@pytest.fixture(scope="session")
def worker_process(core_process: str, redis_backend: dict[str, str]) -> Generator[None, None, None]:
    env = os.environ | {
        "API_KEY": "test_key",
        "REDIS_URL": redis_backend["url"],
        "REDIS_PASSWORD": redis_backend["password"],
        "TARANIS_CORE_URL": core_process,
    }
    worker_path = str(REPO_ROOT / "src" / "worker")
    proc = subprocess.Popen(
        ["uv", "run", "--directory", worker_path, "python", "-m", "worker"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.poll() is not None:
        output = proc.stdout.read() if proc.stdout else ""
        raise RuntimeError(f"Worker exited immediately. Output:\n{output}")
    try:
        _wait_for_worker_ready(core_process, timeout_seconds=30)
    except Exception as exc:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - best effort cleanup
            proc.kill()
        output = proc.stdout.read() if proc.stdout else ""
        raise RuntimeError(f"Worker failed to become ready: {exc}\nOutput:\n{output}") from exc
    yield
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - best effort cleanup
        proc.kill()


@pytest.fixture(scope="session")
def cron_process(core_process: str, redis_backend: dict[str, str]) -> Generator[None, None, None]:
    env = os.environ | {
        "API_KEY": "test_key",
        "REDIS_URL": redis_backend["url"],
        "REDIS_PASSWORD": redis_backend["password"],
        "TARANIS_CORE_URL": core_process,
    }
    worker_path = str(REPO_ROOT / "src" / "worker")
    proc = subprocess.Popen(
        ["uv", "run", "--directory", worker_path, "python", "start_cron_scheduler.py"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.poll() is not None:
        output = proc.stdout.read() if proc.stdout else ""
        raise RuntimeError(f"Cron scheduler exited immediately. Output:\n{output}")
    yield
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - best effort cleanup
        proc.kill()


@pytest.fixture
def wordlist_server(tmp_path: Path) -> Generator[str, None, None]:
    data = "value,category\nalpha,include\nbeta,include\n"
    (tmp_path / "wordlist.csv").write_text(data, encoding="utf-8")

    def handler(*args, **kwargs):
        return SimpleHTTPRequestHandler(*args, directory=str(tmp_path), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/wordlist.csv"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture
def rss_server(tmp_path: Path) -> Generator[str, None, None]:
    item_html = "<html><body><h1>Test Item</h1><p>Hello from item.</p></body></html>"
    (tmp_path / "item1.html").write_text(item_html, encoding="utf-8")

    def handler(*args, **kwargs):
        return SimpleHTTPRequestHandler(*args, directory=str(tmp_path), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>http://127.0.0.1:{server.server_port}/</link>
    <description>Test feed for e2e</description>
    <item>
      <title>Test Item</title>
      <link>http://127.0.0.1:{server.server_port}/item1.html</link>
      <description>Test item description</description>
      <pubDate>Mon, 09 Feb 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    (tmp_path / "feed.xml").write_text(rss_feed, encoding="utf-8")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/feed.xml"
    server.shutdown()
    thread.join(timeout=5)


def _login(core_url: str) -> str:
    response = requests.post(
        f"{core_url}/auth/login",
        json={"username": "admin", "password": "admin"},
        timeout=5,
    )
    response.raise_for_status()
    if token := response.json().get("access_token"):
        return token
    else:
        raise RuntimeError("No access_token in auth response")


def _wait_for_worker_ready(core_url: str, timeout_seconds: int = 30) -> None:
    """
    Wait until at least one worker instance is reported by /config/workers.
    Accepts both legacy list responses and newer dict-based responses.
    """
    token = _login(core_url)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
    deadline = time.monotonic() + timeout_seconds
    last_payload = None
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/workers", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            # Legacy shape: plain list of workers
            if isinstance(last_payload, list) and last_payload:
                return
            # Possible new shape: {"items": [...]}
            if isinstance(last_payload, dict):
                items = last_payload.get("items")
                if isinstance(items, list) and items:
                    return
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for worker to register. Last payload: {last_payload}")


def _poll_wordlist_entries(
    core_url: str,
    headers: dict[str, str],
    wordlist_id: int,
    timeout_seconds: int = 30,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/word-lists/{wordlist_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            if (last_payload.get("entry_count") or 0) > 0:
                return last_payload
        time.sleep(0.5)
    raise RuntimeError(f"Word list did not update within {timeout_seconds}s. Last payload: {last_payload}")


def _poll_task_result(
    core_url: str,
    headers: dict[str, str],
    task_id: str,
    timeout_seconds: int = 30,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/task-results/{task_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            if last_payload.get("status") == "SUCCESS":
                return last_payload
        time.sleep(0.5)
    raise RuntimeError(f"Task {task_id} did not report SUCCESS within {timeout_seconds}s. Last payload: {last_payload}")


def _poll_collector_task_result(
    core_url: str,
    headers: dict[str, str],
    source_name: str,
    timeout_seconds: int = 90,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/task-results", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            items = last_payload.get("items") if isinstance(last_payload, dict) else None
            if isinstance(items, list):
                for item in items:
                    if item.get("task") == "collector_task" and source_name in (item.get("result") or ""):
                        if item.get("status") == "SUCCESS":
                            return item
        time.sleep(1.0)
    raise RuntimeError(
        f"Collector task for source '{source_name}' did not report SUCCESS within {timeout_seconds}s. "
        f"Last payload: {last_payload}"
    )


@pytest.mark.e2e_ci
def test_rq_wordlist_queue_flow(
    core_process: str,
    worker_process: None,
    wordlist_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

    create_resp = requests.post(
        f"{core_process}/config/word-lists",
        headers=headers,
        json={"name": "E2E Wordlist", "description": "E2E", "usage": 0, "link": wordlist_server},
        timeout=5,
    )
    create_resp.raise_for_status()
    wordlist_id = create_resp.json().get("id")
    assert wordlist_id, "wordlist id missing"

    enqueue_resp = requests.post(
        f"{core_process}/config/word-lists/gather/{wordlist_id}",
        headers=headers,
        timeout=5,
    )
    enqueue_resp.raise_for_status()

    payload = _poll_wordlist_entries(core_process, headers, wordlist_id)
    assert (payload.get("entry_count") or 0) > 0


@pytest.mark.e2e_ci
def test_rq_cleanup_token_blacklist(
    core_process: str,
    worker_process: None,
    redis_backend: dict[str, str],
) -> None:
    """
    Enqueue the cleanup_token_blacklist job and assert that core reports it as SUCCESS.
    We enqueue via the dotted path so it matches how the worker discovers the task.
    """
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"], decode_responses=False)
    # Use explicit queue name to match worker configuration.
    queue = Queue("misc", connection=redis_conn)
    job_id = f"e2e_cleanup_token_blacklist_{int(time.time())}"

    # Enqueue by dotted path, which does not require importing the worker package
    # into the test process and matches the worker's expectations.
    queue.enqueue("worker.misc.misc_tasks.cleanup_token_blacklist", job_id=job_id)

    payload = _poll_task_result(core_process, headers, job_id, timeout_seconds=30)
    assert payload.get("status") == "SUCCESS"


@pytest.mark.e2e_ci
def test_rq_scheduled_collector_cron(
    core_process: str,
    worker_process: None,
    cron_process: None,
    rss_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

    # Create a minimal RSS collector source using the local feed server.
    source_payload = {
        "name": "E2E RSS Source",
        "description": "E2E RSS source for scheduled collector test",
        "type": "RSS_COLLECTOR",
        "parameters": [
            {"parameter": "FEED_URL", "value": rss_server, "type": "text", "rules": "required"},
            {"parameter": "REFRESH_INTERVAL", "value": "*/1 * * * *", "type": "cron_interval"},
        ],
    }
    create_resp = requests.post(
        f"{core_process}/config/osint-sources",
        headers=headers,
        json=source_payload,
        timeout=5,
    )
    create_resp.raise_for_status()
    source_id = create_resp.json().get("id")
    assert source_id, "osint source id missing"

    # Use cron schedule (every minute) and wait for scheduler + worker to execute it.
    payload = _poll_collector_task_result(core_process, headers, source_payload["name"], timeout_seconds=90)
    assert payload.get("status") == "SUCCESS"
