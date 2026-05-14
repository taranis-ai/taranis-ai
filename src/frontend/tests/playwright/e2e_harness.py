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
    docker_bin = shutil.which("docker")
    if docker_bin:
        if subprocess.run([docker_bin, "compose", "version"], capture_output=True, check=False).returncode == 0:
            if subprocess.run([docker_bin, "info"], capture_output=True, check=False).returncode == 0:
                return "docker compose"

    if shutil.which("podman-compose"):
        podman_bin = shutil.which("podman")
        if podman_bin and subprocess.run([podman_bin, "info"], capture_output=True, check=False).returncode == 0:
            return "podman-compose"

    pytest.skip("docker compose or podman-compose is not available - skipping docker-backed tests")


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
    cmd.extend(["-f", compose_file, "logs"])
    if "podman" not in docker_compose_command:
        cmd.append("--no-color")
    cmd.extend(services)

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
