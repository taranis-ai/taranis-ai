import re
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import redis
import responses

from tests.core_requests import CoreRequestClient
from tests.playwright.e2e_harness import (
    compose_logs,
    docker_cleanup_commands,
    docker_setup_commands,
    require_docker_compose_command,
    wait_for_http_ok,
)


LOCAL_HTTP_URL_PATTERN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")


def _allow_local_http_passthrough() -> None:
    responses.add_passthru(LOCAL_HTTP_URL_PATTERN)


@pytest.fixture(autouse=True)
def allow_local_http_passthrough() -> None:
    _allow_local_http_passthrough()


def _wait_for_admin_login(core_url: str, timeout_seconds: int = 30, poll_interval: float = 0.5) -> None:
    _allow_local_http_passthrough()
    core_client = CoreRequestClient(base_url=core_url)
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = core_client.post(
                "/auth/login",
                json_data={"username": "admin", "password": "admin"},
                timeout_seconds=2,
            )
            if response.json().get("access_token"):
                return
        except Exception as exc:  # pragma: no cover - readiness polling
            last_exc = exc
            time.sleep(poll_interval)
    raise RuntimeError(f"Timed out waiting for admin login at {core_url}: {last_exc}")


def _wait_for_redis(port: int, timeout_seconds: int = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    client = redis.Redis(host="127.0.0.1", port=port, password=None)
    while time.monotonic() < deadline:
        try:
            if client.ping():
                return
        except Exception as exc:  # pragma: no cover - readiness polling
            last_exc = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for redis on port {port}: {last_exc}")


def _wait_for_worker_registration(core_url: str, timeout_seconds: int = 30) -> None:
    _allow_local_http_passthrough()
    core_client = CoreRequestClient(base_url=core_url)
    deadline = time.monotonic() + timeout_seconds
    last_payload = None
    while time.monotonic() < deadline:
        response = core_client.post(
            "/auth/login",
            json_data={"username": "admin", "password": "admin"},
            timeout_seconds=5,
        )
        token = response.json().get("access_token")
        if not token:
            time.sleep(0.5)
            continue

        worker_client = core_client.with_access_token(token)
        response = worker_client.get("/config/workers", raise_for_status=False, timeout_seconds=5)
        if response.status_code == 200:
            last_payload = response.json()
            if isinstance(last_payload, list) and last_payload:
                return
            if isinstance(last_payload, dict):
                items = last_payload.get("items")
                if isinstance(items, list) and items:
                    return
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for worker to register. Last payload: {last_payload}")


def _wait_for_cron_leader(redis_url: str, timeout_seconds: int = 15) -> None:
    redis_conn = redis.from_url(redis_url, password=None, decode_responses=False)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if redis_conn.get("rq:cron:leader"):
            return
        time.sleep(0.5)
    raise RuntimeError("Cron scheduler did not become active in Redis")


@pytest.fixture(scope="session")
def docker_compose_file() -> str:
    return str(Path(__file__).parent / "compose.e2e.yml")


@pytest.fixture(scope="session")
def docker_compose_command() -> str:
    return require_docker_compose_command()


@pytest.fixture(scope="session")
def docker_setup(docker_compose_command: str) -> list[str]:
    return docker_setup_commands(docker_compose_command)


@pytest.fixture(scope="session")
def docker_cleanup() -> list[str]:
    return docker_cleanup_commands()


@pytest.fixture(scope="session")
def core_process(
    docker_services,
    docker_compose_command: str,
    docker_compose_file: str,
    docker_compose_project_name: str,
) -> Generator[str, None, None]:
    core_port = docker_services.port_for("core", 8080)
    base_url = f"http://127.0.0.1:{core_port}/api"

    try:
        _allow_local_http_passthrough()
        wait_for_http_ok(f"{base_url}/isalive", timeout_seconds=60)
        _wait_for_admin_login(base_url, timeout_seconds=60)
        yield base_url
    except Exception as exc:
        logs = compose_logs(
            docker_compose_command,
            docker_compose_file,
            "core",
            "redis",
            project_name=docker_compose_project_name,
        )
        raise RuntimeError(f"Failed to start core e2e services: {exc}\n\nCompose logs:\n{logs}") from exc


@pytest.fixture(scope="session")
def redis_backend(
    docker_services,
    docker_compose_command: str,
    docker_compose_file: str,
    docker_compose_project_name: str,
) -> Generator[dict[str, str], None, None]:
    redis_port = docker_services.port_for("redis", 6379)
    try:
        _wait_for_redis(redis_port)
        yield {"url": f"redis://127.0.0.1:{redis_port}/0", "password": ""}
    except Exception as exc:
        logs = compose_logs(
            docker_compose_command,
            docker_compose_file,
            "redis",
            project_name=docker_compose_project_name,
        )
        raise RuntimeError(f"Failed to start redis e2e service: {exc}\n\nCompose logs:\n{logs}") from exc


@pytest.fixture(scope="session")
def worker_process(
    core_process: str,
    docker_compose_command: str,
    docker_compose_file: str,
    docker_compose_project_name: str,
) -> Generator[None, None, None]:
    try:
        _wait_for_worker_registration(core_process, timeout_seconds=180)
        yield
    except Exception as exc:
        logs = compose_logs(
            docker_compose_command,
            docker_compose_file,
            "worker",
            "core",
            "redis",
            "testdata",
            project_name=docker_compose_project_name,
        )
        raise RuntimeError(f"Worker failed to become ready: {exc}\n\nCompose logs:\n{logs}") from exc


@pytest.fixture(scope="session")
def cron_process(
    redis_backend: dict[str, str],
    docker_compose_command: str,
    docker_compose_file: str,
    docker_compose_project_name: str,
) -> Generator[None, None, None]:
    try:
        _wait_for_cron_leader(redis_backend["url"], timeout_seconds=120)
        yield
    except Exception as exc:
        logs = compose_logs(
            docker_compose_command,
            docker_compose_file,
            "cron",
            "core",
            "redis",
            project_name=docker_compose_project_name,
        )
        raise RuntimeError(f"Cron scheduler failed to become ready: {exc}\n\nCompose logs:\n{logs}") from exc


@pytest.fixture(scope="session")
def wordlist_server() -> Generator[str, None, None]:
    yield "http://testdata/wordlist.csv"


@pytest.fixture(scope="session")
def rss_server() -> Generator[str, None, None]:
    yield "http://testdata/feed.xml"
