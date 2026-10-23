"""Build an isolated master template and install a checkout-local Git hook."""

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from psycopg import sql


SETUP_DATABASE = """
from flask import Flask
from core.managers import db_manager

app = Flask(__name__)
app.config.from_object("core.config.Config")
with app.app_context():
    db_manager.initialize(app, initial_setup=True)
"""
HOOK_LABEL = "# taranis-branch-databases checkout dispatcher"


class BranchDatabases:
    def __init__(self, config):
        self.config = config
        self.root = config.root
        # Hooks export repository-local Git settings. Do not carry them into the
        # temporary master worktree (or another checkout invoked by its hooks).
        local_keys = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--local-env-vars"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        self.environment = {key: value for key, value in os.environ.items() if key not in local_keys}
        self.directory = Path(self.git("rev-parse", "--absolute-git-dir")) / "taranis-branch-databases"
        self.directory.mkdir(mode=0o700, exist_ok=True)
        self.identity = hashlib.sha256(str(self.directory).encode()).hexdigest()[:12]
        self.prefix = f"tdb_{self.identity}_"
        self.marker = f"taranis-branch-databases:{self.identity}:"

    def git(self, *arguments: str) -> str:
        try:
            return subprocess.run(
                ["git", "-C", str(self.root), *arguments],
                env=self.environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            ).stdout.strip()
        except subprocess.SubprocessError:
            raise RuntimeError("Git operation failed. Check origin/master and Git access, then retry dev/db.sh refresh.") from None

    def databases(self, connection) -> dict[str, str]:
        rows = connection.execute("SELECT datname, shobj_description(oid, 'pg_database') FROM pg_database")
        return {name: comment or "" for name, comment in rows if name.startswith(self.prefix)}

    def drop(self, connection, name: str):
        comment = self.databases(connection).get(name)
        if comment is None:
            return
        if not comment.startswith(self.marker):
            raise RuntimeError("A managed database name belongs to an unrecognized database; nothing was deleted.")
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))

    def create(self, connection, name: str, kind: str, template: str | None = None):
        if name in self.databases(connection):
            raise RuntimeError("A managed database name already exists; inspect it before retrying.")
        statement = sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(name), sql.Identifier(template or "template0"))
        connection.execute(statement)
        connection.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(self.marker + kind)))

    def master_template(self, connection) -> str:
        self.git("fetch", "--no-tags", "origin", "+refs/heads/master:refs/remotes/origin/master")
        revision = self.git("rev-parse", "refs/remotes/origin/master^{commit}")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise RuntimeError("origin/master did not resolve to a supported Git commit.")
        name = self.prefix + "m_" + revision
        existing = self.databases(connection).get(name)
        if existing == self.marker + "master:" + revision:
            return name
        if existing is not None:
            # A failed, interrupted initialization is never a usable template.
            self.drop(connection, name)
        self.create(connection, name, "building")
        try:
            with tempfile.TemporaryDirectory(prefix="taranis-master-") as temporary:
                worktree = Path(temporary) / "master"
                self.git("-c", "core.hooksPath=/dev/null", "worktree", "add", "--detach", str(worktree), revision)
                try:
                    environment = (
                        self.environment
                        | self.config.core
                        | {
                            "DB_DATABASE": name,
                            "DISABLE_SCHEDULER": "true",
                            "DEBUG": "true",
                            "TARANIS_CORE_SENTRY_DSN": "",
                            "OTEL_EXPORTER_OTLP_ENDPOINT": "",
                        }
                    )
                    # Keep diagnostics private; dependency/setup output can contain local settings.
                    log_path = self.directory / "template-setup.log"
                    with log_path.open("w", encoding="utf-8") as log:
                        log_path.chmod(0o600)
                        subprocess.run(
                            ["uv", "run", "--frozen", "python", "-c", SETUP_DATABASE],
                            cwd=worktree / "src/core",
                            env=environment,
                            stdout=log,
                            stderr=log,
                            check=True,
                        )
                finally:
                    self.git("worktree", "remove", "--force", str(worktree))
            connection.execute(sql.SQL("ALTER DATABASE {} ALLOW_CONNECTIONS false").format(sql.Identifier(name)))
            connection.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(self.marker + "master:" + revision))
            )
        except BaseException:
            self.drop(connection, name)
            raise
        print(f"Master template ready at {revision[:12]}.")
        return name

    def replacement(self, connection, template: str) -> str:
        name = self.prefix + ("b" if self.config.selected == self.prefix + "a" else "a")
        self.drop(connection, name)
        self.create(connection, name, "disposable", template)
        return name

    def cleanup(self, connection, template: str, selected: str):
        for name, comment in self.databases(connection).items():
            if name not in {template, selected} and comment.startswith(self.marker):
                self.drop(connection, name)

    def hook_path(self) -> Path:
        hook = Path(self.git("rev-parse", "--path-format=absolute", "--git-path", "hooks/post-checkout"))
        common = Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        if not hook.is_relative_to(common):
            raise RuntimeError("Use repository-local Git hooks before enabling; shared external hooks are not modified.")
        if hook.is_symlink():
            raise RuntimeError("The existing post-checkout hook is a symlink. Use a regular repository-local hook before enabling.")
        if (not hook.exists() or HOOK_LABEL not in hook.read_text(encoding="utf-8")) and hook.with_name(
            "post-checkout.before-taranis"
        ).exists():
            raise RuntimeError("A saved post-checkout hook already exists; inspect the hooks before enabling.")
        return hook

    def install_hook(self, session: str):
        # Keep a snapshot outside tracked files so checkout of master can still
        # execute the lifecycle before this feature has been merged there.
        for name in ("databases.py", "database_processes.py", "database_branches.py"):
            source, destination = Path(__file__).with_name(name), self.directory / name
            if source.resolve() != destination.resolve():
                shutil.copyfile(source, destination)
        runner = self.directory / "run"
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("Install uv before enabling branch databases.")
        runner.write_text(
            "#!/bin/sh\nexec "
            + shlex.join(
                [
                    uv,
                    "run",
                    "--project",
                    str(self.root / "src/core"),
                    "--frozen",
                    "--no-sync",
                    "python",
                    str(self.directory / "databases.py"),
                    "--root",
                    str(self.root),
                    "--session",
                    session,
                ]
            )
            + ' "$@"\n',
            encoding="utf-8",
        )
        runner.chmod(0o700)
        (self.directory / "root").write_text(str(self.root) + "\n", encoding="utf-8")
        hook = self.hook_path()
        hook.parent.mkdir(parents=True, exist_ok=True)
        if not hook.exists() or HOOK_LABEL not in hook.read_text(encoding="utf-8"):
            previous = hook.with_name("post-checkout.before-taranis")
            original = ""
            if hook.exists():
                hook.rename(previous)
                original = f'if [ -x {shlex.quote(str(previous))} ]; then\n  {shlex.quote(str(previous))} "$@" || exit $?\nfi\n'
            hook.write_text(
                "#!/bin/sh\n"
                + HOOK_LABEL
                + "\n"
                + original
                + 'runtime="$(git rev-parse --absolute-git-dir)/taranis-branch-databases"\n'
                + 'if [ "${3:-0}" = 1 ] && [ -f "$runtime/enabled" ] &&\n'
                + '  [ "$(git rev-parse --show-toplevel)" = "$(cat "$runtime/root")" ]; then\n'
                + '  "$runtime/run" refresh\nfi\n',
                encoding="utf-8",
            )
            hook.chmod(0o700)
        (self.directory / "enabled").touch(mode=0o600)
        print("Automatic branch databases enabled for this checkout. Existing post-checkout hooks are preserved.")
