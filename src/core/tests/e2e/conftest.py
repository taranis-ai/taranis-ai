import os
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import redis
import requests

from testsupport.docker_harness import (
    compose_logs,
    docker_cleanup_commands,
    docker_setup_commands,
    require_docker_compose_command,
    wait_for_http_ok,
)


os.environ.setdefault(
    "TARANIS_E2E_UV_CACHE_DIR",
    os.getenv("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
)


def _wait_for_admin_login(core_url: str, timeout_seconds: int = 30, poll_interval: float = 0.5) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = requests.post(
                f"{core_url}/auth/login",
                json={"username": "admin", "password": "admin"},
                timeout=2,
            )
            response.raise_for_status()
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
    deadline = time.monotonic() + timeout_seconds
    last_payload = None
    while time.monotonic() < deadline:
        response = requests.post(
            f"{core_url}/auth/login",
            json={"username": "admin", "password": "admin"},
            timeout=5,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            time.sleep(0.5)
            continue

        headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
        resp = requests.get(f"{core_url}/config/workers", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
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
    return str(Path(__file__).parent / "docker-compose.e2e.yml")


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
            "worker_setup",
            "core",
            "redis",
            "fixtures",
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
            "worker_setup",
            "core",
            "redis",
            project_name=docker_compose_project_name,
        )
        raise RuntimeError(f"Cron scheduler failed to become ready: {exc}\n\nCompose logs:\n{logs}") from exc


@pytest.fixture(scope="session")
def wordlist_server() -> Generator[str, None, None]:
    yield "http://fixtures/wordlist.csv"


@pytest.fixture(scope="session")
def rss_server() -> Generator[str, None, None]:
    yield "http://fixtures/feed.xml"
