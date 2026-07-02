from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from tests.load.load_support.run_locust import build_locust_command, run_locust


def test_build_locust_command_uses_environment_overrides() -> None:
    command = build_locust_command(
        {
            "TARGET_HOST": "http://example.test",
            "LOCUST_USERS": "4",
            "LOCUST_SPAWN_RATE": "2",
            "LOCUST_RUN_TIME": "10m",
        }
    )

    assert command == [
        "locust",
        "--headless",
        "--only-summary",
        "--exit-code-on-error",
        "1",
        "--stop-timeout",
        "30",
        "--host",
        "http://example.test",
        "--users",
        "4",
        "--spawn-rate",
        "2",
        "--run-time",
        "10m",
        "--html",
        "/artifacts/locust-report.html",
        "--csv",
        "/artifacts/locust",
        "-f",
        "/workspace/src/frontend/tests/load/locustfile.py",
    ]


def test_run_locust_runs_from_screenshot_directory_and_formats_report(tmp_path: Path) -> None:
    calls: list[tuple[Sequence[str], Path, bool]] = []

    def runner(args: Sequence[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[object]:
        calls.append((args, cwd, check))
        return subprocess.CompletedProcess(args=args, returncode=7)

    formatted_paths: list[Path] = []
    report_path = tmp_path / "locust-report.html"
    report_path.write_text("<html></html>", encoding="utf-8")

    status = run_locust(
        env={},
        artifacts_dir=tmp_path,
        runner=runner,
        formatter=formatted_paths.append,
    )

    assert status == 7
    assert calls == [
        (
            build_locust_command({}),
            tmp_path / "screenshots",
            False,
        )
    ]
    assert (tmp_path / "screenshots").is_dir()
    assert formatted_paths == [report_path]


def test_run_locust_returns_formatting_error_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def runner(args: Sequence[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[object]:
        return subprocess.CompletedProcess(args=args, returncode=0)

    def formatter(path: Path) -> None:
        raise ValueError("invalid report")

    report_path = tmp_path / "locust-report.html"
    report_path.write_text("<html></html>", encoding="utf-8")

    status = run_locust(
        env={},
        artifacts_dir=tmp_path,
        runner=runner,
        formatter=formatter,
    )

    assert status == 1
    assert f"Failed to format Locust report {report_path}: invalid report" in capsys.readouterr().err
