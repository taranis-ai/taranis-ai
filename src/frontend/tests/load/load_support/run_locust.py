from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from tests.load.load_support.format_locust_report import format_report_file

DEFAULT_ARTIFACT_DIR = Path("/artifacts")
LOCUST_FILE = "/workspace/src/frontend/tests/load/locustfile.py"


class CommandRunner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[object]: ...


def read_env(env: Mapping[str, str], name: str, default: str) -> str:
    return env.get(name) or default


def build_locust_command(env: Mapping[str, str]) -> list[str]:
    return [
        "locust",
        "--headless",
        "--only-summary",
        "--exit-code-on-error",
        "1",
        "--stop-timeout",
        "30",
        "--host",
        read_env(env, "TARGET_HOST", "http://ingress:8080"),
        "--users",
        read_env(env, "LOCUST_USERS", "1"),
        "--spawn-rate",
        read_env(env, "LOCUST_SPAWN_RATE", "1"),
        "--run-time",
        read_env(env, "LOCUST_RUN_TIME", "2m"),
        "--html",
        "/artifacts/locust-report.html",
        "--csv",
        "/artifacts/locust",
        "-f",
        LOCUST_FILE,
    ]


def run_locust(
    *,
    env: Mapping[str, str] = os.environ,
    artifacts_dir: Path = DEFAULT_ARTIFACT_DIR,
    runner: CommandRunner = subprocess.run,
    formatter: Callable[[Path], None] = format_report_file,
) -> int:
    screenshots_dir = artifacts_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    result = runner(build_locust_command(env), cwd=screenshots_dir, check=False)
    report_path = artifacts_dir / "locust-report.html"
    if report_path.exists():
        try:
            formatter(report_path)
        except Exception as exc:
            print(f"Failed to format Locust report {report_path}: {exc}", file=sys.stderr)
            return 1

    return result.returncode


def main() -> int:
    return run_locust()


if __name__ == "__main__":
    raise SystemExit(main())
