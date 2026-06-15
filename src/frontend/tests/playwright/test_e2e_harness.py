import subprocess

import e2e_harness
import pytest


def _patch_which(monkeypatch, commands: dict[str, str | None]) -> None:
    monkeypatch.setattr(e2e_harness.shutil, "which", lambda command: commands.get(command))


def _patch_run(monkeypatch, results: dict[tuple[str, ...], subprocess.CompletedProcess]) -> None:
    def fake_run(command, **kwargs):
        return results.get(tuple(command), subprocess.CompletedProcess(command, 1))

    monkeypatch.setattr(e2e_harness.subprocess, "run", fake_run)


def _completed(command: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def test_require_docker_compose_command_uses_docker_when_available(monkeypatch):
    docker_bin = "/usr/bin/docker"
    _patch_which(monkeypatch, {"docker": docker_bin})
    _patch_run(
        monkeypatch,
        {
            (docker_bin, "--version"): _completed([docker_bin, "--version"], stdout="Docker version 28.0.0"),
            (docker_bin, "compose", "version"): _completed([docker_bin, "compose", "version"]),
            (docker_bin, "info"): _completed([docker_bin, "info"]),
        },
    )

    assert e2e_harness.require_docker_compose_command() == "docker compose"


def test_require_docker_compose_command_uses_podman_compose(monkeypatch):
    docker_bin = "/usr/bin/docker"
    podman_bin = "/usr/bin/podman"
    _patch_which(monkeypatch, {"docker": docker_bin, "podman": podman_bin, "podman-compose": "/usr/bin/podman-compose"})
    _patch_run(
        monkeypatch,
        {
            (docker_bin, "--version"): _completed([docker_bin, "--version"], stdout="podman version 5.0.0"),
            (podman_bin, "info"): _completed([podman_bin, "info"]),
        },
    )

    assert e2e_harness.require_docker_compose_command() == "podman-compose"


def test_require_docker_compose_command_uses_podman_compose_subcommand(monkeypatch):
    docker_bin = "/usr/bin/docker"
    podman_bin = "/usr/bin/podman"
    _patch_which(monkeypatch, {"docker": docker_bin, "podman": podman_bin})
    _patch_run(
        monkeypatch,
        {
            (docker_bin, "--version"): _completed([docker_bin, "--version"], stdout="podman version 5.0.0"),
            (podman_bin, "info"): _completed([podman_bin, "info"]),
            (podman_bin, "compose", "version"): _completed([podman_bin, "compose", "version"]),
        },
    )

    assert e2e_harness.require_docker_compose_command() == "podman compose"


def test_require_docker_compose_command_skips_when_unavailable(monkeypatch):
    _patch_which(monkeypatch, {})
    _patch_run(monkeypatch, {})

    with pytest.raises(pytest.skip.Exception):
        e2e_harness.require_docker_compose_command()
