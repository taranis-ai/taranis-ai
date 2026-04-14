import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests


os.environ.setdefault(
    "TARANIS_E2E_UV_CACHE_DIR",
    os.getenv("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
)


def wait_for_http_ok(url: str, timeout_seconds: int = 20, poll_interval: float = 0.5) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            resp.raise_for_status()
            return
        except Exception as exc:  # pragma: no cover - readiness polling
            last_exc = exc
            time.sleep(poll_interval)
    raise RuntimeError(f"Timed out waiting for {url}: {last_exc}")


def require_docker_compose_command() -> str:
    if shutil.which("podman-compose"):
        podman_bin = shutil.which("podman")
        if podman_bin and subprocess.run([podman_bin, "info"], capture_output=True, check=False).returncode != 0:
            pytest.skip("podman-compose is installed but podman is not available - skipping docker-backed tests")
        return "podman-compose"

    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.skip("docker is not available - skipping docker-backed tests")

    if subprocess.run([docker_bin, "compose", "version"], capture_output=True, check=False).returncode != 0:
        pytest.skip("docker compose is not available - skipping docker-backed tests")

    if subprocess.run([docker_bin, "info"], capture_output=True, check=False).returncode != 0:
        pytest.skip("docker daemon is not available - skipping docker-backed tests")

    return "docker compose"


def docker_setup_commands(docker_compose_command: str) -> list[str]:
    up_cmd = "up -d" if "podman" in docker_compose_command else "up -d --wait"
    return ["down -v --remove-orphans", up_cmd]


def docker_cleanup_commands() -> list[str]:
    return ["down -v --remove-orphans"]


def compose_logs(
    docker_compose_command: str,
    compose_file: str,
    *services: str,
    project_name: str | None = None,
) -> str:
    cmd = [*shlex.split(docker_compose_command)]
    if project_name:
        cmd.extend(["-p", project_name])
    cmd.extend(["-f", compose_file, "logs", "--no-color", *services])

    result = subprocess.run(
        cmd,
        cwd=Path(compose_file).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout.strip()
    if result.stderr.strip():
        output = f"{output}\n\nstderr:\n{result.stderr.strip()}".strip()
    return output or "(no compose logs available)"