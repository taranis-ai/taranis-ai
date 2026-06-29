import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests


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


def _command_succeeds(command: list[str]) -> bool:
    return subprocess.run(command, capture_output=True, check=False).returncode == 0


def _docker_is_podman(docker_bin: str) -> bool:
    result = subprocess.run([docker_bin, "--version"], capture_output=True, text=True, check=False)
    return "podman" in f"{result.stdout}\n{result.stderr}".lower()


def require_docker_compose_command() -> str:
    docker_bin = shutil.which("docker")
    if docker_bin and not _docker_is_podman(docker_bin):
        if _command_succeeds([docker_bin, "compose", "version"]) and _command_succeeds([docker_bin, "info"]):
            return "docker compose"

    podman_bin = shutil.which("podman")
    if podman_bin and _command_succeeds([podman_bin, "info"]):
        if shutil.which("podman-compose"):
            return "podman-compose"
        if _command_succeeds([podman_bin, "compose", "version"]):
            return "podman compose"

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
