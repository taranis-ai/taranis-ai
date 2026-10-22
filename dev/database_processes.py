"""Pause the standard development tmux panes while changing databases."""

import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener


SHELLS = {"bash", "zsh", "fish", "sh"}
CONNECTION_ENVIRONMENT_KEYS = (
    "DB_URL",
    "DB_USER",
    "DB_PASSWORD",
    "DB_DATABASE",
    "SQLALCHEMY_DATABASE_URI",
    "SQLALCHEMY_SCHEMA",
    "REDIS_URL",
    "REDIS_PASSWORD",
    "CACHE_REDIS_URL",
    "CACHE_REDIS_PASSWORD",
    "FLASK_RUN_PORT",
    "FLASK_RUN_HOST",
    "APPLICATION_ROOT",
    "TARANIS_CORE_URL",
)
APP_SCRIPTS = {
    "core": ("core", "install_and_run_dev.sh"),
    "frontend": ("frontend", "install_and_run_dev.sh"),
    "worker": ("worker", "install_and_run_dev.sh"),
    "cron": ("worker", "install_and_run_cron.sh"),
    "rq-dashboard": ("worker", "install_and_run_rq_dashboard.sh"),
}
PANE_FORMAT = "\t".join(
    f"#{{{field}}}" for field in ("window_name", "pane_id", "pane_pid", "pane_current_path", "pane_current_command", "pane_start_command")
)


@dataclass(frozen=True)
class Pane:
    target: str
    shell_pid: int
    directory: Path
    command: str
    start_command: str


class TmuxProcesses:
    """Keep the existing windows and scrollback when stopping and restarting apps."""

    def __init__(
        self,
        root: Path,
        session: str = "taranis",
        core_url: str = "http://127.0.0.1:5001/api/health",
        frontend_url: str = "http://127.0.0.1:5002/frontend/health",
    ):
        self.root = root.resolve()
        self.session = session
        self.core_url = core_url
        self.frontend_url = frontend_url
        self.panes: dict[str, Pane] = {}
        self.http = build_opener(ProxyHandler({}))

    @staticmethod
    def _command(*arguments: str) -> str:
        try:
            result = subprocess.run(arguments, capture_output=True, text=True, check=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            raise RuntimeError("Unable to inspect or control the development tmux session.") from None
        return result.stdout

    def _read_panes(self) -> dict[str, Pane]:
        output = self._command("tmux", "list-panes", "-s", "-t", f"={self.session}", "-F", PANE_FORMAT)
        panes = {}
        for line in output.splitlines():
            fields = line.split("\t")
            if len(fields) != 6 or not fields[2].isdigit():
                raise RuntimeError("Unable to inspect development tmux panes.")
            window, target, pid, directory, command, start_command = fields
            if window in panes:
                raise RuntimeError("Database operations require one pane per development tmux window.")
            panes[window] = Pane(target, int(pid), Path(directory).resolve(), command, start_command)
        return panes

    def preflight(self) -> None:
        """Refuse to interrupt a customized session or another checkout's processes."""
        panes = self._read_panes()
        if not {"core", "frontend", "worker"}.issubset(panes):
            raise RuntimeError("Start the standard development tmux workflow before changing databases.")
        if any(pane.target == os.environ.get("TMUX_PANE") for name, pane in panes.items() if name in APP_SCRIPTS):
            raise RuntimeError("Run database commands from a terminal outside the application tmux panes.")
        for window, pane in panes.items():
            if window not in APP_SCRIPTS and window != "tailwind":
                raise RuntimeError("The development tmux session contains an unrecognized window.")
            component = "frontend" if window == "tailwind" else APP_SCRIPTS[window][0]
            if pane.directory != self.root / "src" / component:
                raise RuntimeError("A development tmux pane belongs to another directory or checkout.")
            if pane.start_command:
                try:
                    startup = shlex.split(pane.start_command)
                except ValueError:
                    raise RuntimeError("A development tmux pane uses an unrecognized startup command.") from None
                shell_flags = {"-l", "-i", "--login", "--noprofile", "--norc"}
                if not startup or Path(startup[0]).name not in SHELLS or not set(startup[1:]).issubset(shell_flags):
                    raise RuntimeError("A development tmux pane uses a custom startup command.")
            if window == "tailwind":
                continue
            supported = pane.command in SHELLS | {"uv", "flask", "rq-dashboard"}
            supported |= bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?|taranis-[\w-]+", pane.command))
            if not supported:
                raise RuntimeError("A development tmux pane is running an unrecognized command.")
        self.panes = panes

    def _current_panes(self) -> dict[str, Pane]:
        if not self.panes:
            raise RuntimeError("Inspect the development tmux session before controlling its processes.")
        current = self._read_panes()
        if current.keys() != self.panes.keys() or any(
            (pane.target, pane.shell_pid, pane.directory) != (current[name].target, current[name].shell_pid, current[name].directory)
            for name, pane in self.panes.items()
        ):
            raise RuntimeError("The development tmux session changed during the database operation.")
        return current

    def _process_parents(self) -> dict[int, int]:
        output = self._command("ps", "-axo", "pid=,ppid=")
        return {int(fields[0]): int(fields[1]) for line in output.splitlines() if len(fields := line.split()) == 2}

    def _idle_apps(self, processes: dict[int, int] | None = None) -> set[str]:
        current = self._current_panes()
        parents = set((self._process_parents() if processes is None else processes).values())
        # A shell running an install script can still be reported as bash; wait
        # for its children too so workers cannot survive into the next database.
        return {name for name, pane in current.items() if name in APP_SCRIPTS and pane.command in SHELLS and pane.shell_pid not in parents}

    def stop(self) -> None:
        self._current_panes()
        app_names = set(self.panes) & APP_SCRIPTS.keys()
        processes = self._process_parents()
        app_processes = {self.panes[name].shell_pid for name in app_names}
        children = set()
        while children != app_processes:
            children = app_processes.copy()
            app_processes.update(pid for pid, parent in processes.items() if parent in app_processes)
        app_processes.difference_update(self.panes[name].shell_pid for name in app_names)
        for name in app_names:
            self._command("tmux", "send-keys", "-t", self.panes[name].target, "C-c")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            processes = self._process_parents()
            if self._idle_apps(processes) == app_names and not app_processes.intersection(processes):
                return
            time.sleep(0.2)
        raise RuntimeError("Development processes did not stop. Inspect their tmux panes before retrying.")

    def _core_ready(self) -> bool:
        try:
            try:
                response = self.http.open(self.core_url, timeout=2)
            except HTTPError as response:
                # Optional endpoint outages also make Core return 503. Require
                # database and queue readiness without blocking on those endpoints.
                with response:
                    if response.code != 503:
                        return False
                    payload = json.loads(response.read(65536))
            else:
                with response:
                    payload = json.loads(response.read(65536))
            services = payload.get("services", {})
            return (
                services.get("database") == "up"
                and services.get("seed_data") == "up"
                and services.get("broker") in {"up", "n/a"}
                and services.get("workers") in {"up", "n/a"}
            )
        except (OSError, URLError, ValueError, AttributeError):
            return False

    def _frontend_ready(self) -> bool:
        try:
            with self.http.open(self.frontend_url, timeout=2) as response:
                return response.status == 200
        except (OSError, URLError):
            return False

    def start(self, database: str) -> None:
        app_names = set(self.panes) & APP_SCRIPTS.keys()
        if self._idle_apps() != app_names:
            raise RuntimeError("Stop all development application panes before restarting them.")
        for name, (_, script) in APP_SCRIPTS.items():
            if name not in self.panes:
                continue
            # Component .env files own connection settings; old pane exports must
            # not reconnect a process to a different database or Redis server.
            command = "env " + " ".join(f"-u {key}" for key in CONNECTION_ENVIRONMENT_KEYS)
            if name == "core":
                command += f" DB_DATABASE={shlex.quote(database)}"
            command += f" ./{script}"
            target = self.panes[name].target
            self._command("tmux", "send-keys", "-t", target, "C-u")
            self._command("tmux", "send-keys", "-t", target, "-l", command)
            self._command("tmux", "send-keys", "-t", target, "Enter")
        deadline = time.monotonic() + 120
        startup_grace = time.monotonic() + 1
        stable_since = None
        while time.monotonic() < deadline:
            if self._idle_apps() and time.monotonic() >= startup_grace:
                raise RuntimeError("A development process exited during startup. Inspect its tmux pane.")
            if self._core_ready() and self._frontend_ready():
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 2:
                    return
            else:
                stable_since = None
            time.sleep(0.2)
        raise RuntimeError("Development services did not become ready. Inspect their tmux panes.")
