"""Exercise database switching against a private, real tmux server."""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database_processes import TmuxProcesses


@unittest.skipUnless(shutil.which("tmux"), "tmux is required for the development lifecycle check")
class DatabaseProcessesTest(unittest.TestCase):
    def test_switch_reuses_panes_and_stops_application_children(self):
        with tempfile.TemporaryDirectory(prefix="taranis-db-processes-") as temporary:
            root = Path(temporary)
            previous_environment = {name: os.environ.get(name) for name in ("TMUX_TMPDIR", "TMUX", "TMUX_PANE")}
            os.environ["TMUX_TMPDIR"] = temporary
            os.environ.pop("TMUX", None)
            os.environ.pop("TMUX_PANE", None)
            try:
                urls = {}
                for name in ("core", "frontend", "worker"):
                    directory = root / "src" / name
                    directory.mkdir(parents=True)
                    if name == "worker":
                        command = "exec python3 -c 'import time; time.sleep(300)'"
                    else:
                        with socket.socket() as listener:
                            listener.bind(("127.0.0.1", 0))
                            port = listener.getsockname()[1]
                        route = "api/health" if name == "core" else "login"
                        response = directory / route
                        response.parent.mkdir(exist_ok=True)
                        response.write_text(
                            '{"services": {"database": "up", "seed_data": "up", "broker": "up", "workers": "up"}}'
                            if name == "core"
                            else "Login"
                        )
                        urls[name] = f"http://127.0.0.1:{port}/{route}"
                        command = f"exec python3 -m http.server {port} --bind 127.0.0.1"
                    script = directory / "install_and_run_dev.sh"
                    script.write_text('#!/bin/sh\nprintf "%s" "${DB_DATABASE:-}" > selected-database\n' + command + "\n")
                    script.chmod(0o700)
                    tmux_command = (
                        ["tmux", "-f", "/dev/null", "new-session", "-d", "-s", "database-test"]
                        if name == "core"
                        else ["tmux", "new-window", "-t", "=database-test"]
                    )
                    subprocess.run(
                        [*tmux_command, "-n", name, "-c", str(directory), "/bin/sh"],
                        check=True,
                        capture_output=True,
                    )
                processes = TmuxProcesses(root, "database-test", urls["core"], urls["frontend"])
                processes.preflight()
                original_panes = {name: pane.target for name, pane in processes.panes.items()}
                processes.start("taranis_first")
                self.assertEqual((root / "src/core/selected-database").read_text(), "taranis_first")
                processes.stop()
                processes.start("taranis_second")
                self.assertEqual((root / "src/core/selected-database").read_text(), "taranis_second")
                processes.stop()
                processes.preflight()
                self.assertEqual({name: pane.target for name, pane in processes.panes.items()}, original_panes)
                history = subprocess.run(
                    ["tmux", "capture-pane", "-p", "-t", processes.panes["core"].target, "-S", "-"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                self.assertIn("taranis_first", history)
                self.assertIn("taranis_second", history)
            finally:
                subprocess.run(["tmux", "kill-server"], capture_output=True, check=False)
                for name, value in previous_environment.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
