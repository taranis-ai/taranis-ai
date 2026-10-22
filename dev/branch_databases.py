"""Switch a local Git branch and its development database while applications are stopped."""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

import psycopg
from database_processes import APP_SCRIPTS
from databases import (
    DATABASE_OPERATION_LOCK,
    DatabaseSelection,
    DevelopmentConfig,
    clear_redis,
    copy_database,
    database_name,
    interrupted,
    require_database,
    require_idle_databases,
    settings,
)
from redis.exceptions import RedisError


HELPER_FILES = ("dev/switch.sh", "dev/branch_databases.py", "dev/db.sh", "dev/databases.py", "dev/database_processes.py")
ENV_FILES = tuple(f"src/{component}/.env" for component in ("core", "frontend", "worker"))


def git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True, timeout=30, check=False)
    if check and result.returncode:
        raise RuntimeError("Git could not complete the operation. Inspect the checkout before retrying.")
    return result


def git_path(root: Path, name: str) -> Path:
    return (root / git(root, "rev-parse", "--git-path", name).stdout.strip()).absolute()


def require_checkout(root: Path, branch: str, app_names: set[str]):
    if Path(git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve() != root:
        raise ValueError("Run this command for a Git checkout root.")
    if git(root, "symbolic-ref", "--quiet", "HEAD", check=False).returncode:
        raise ValueError("Check out a local branch before using coordinated switching.")
    target = f"refs/heads/{branch}"
    if (
        git(root, "check-ref-format", target, check=False).returncode
        or git(root, "show-ref", "--verify", "--quiet", target, check=False).returncode
    ):
        raise ValueError("The target must be an existing local branch. Create or fetch it explicitly first.")
    if git(root, "status", "--porcelain=v1", "--untracked-files=normal").stdout:
        raise ValueError("The checkout must be clean, including untracked files. Commit or move your work before switching.")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer", "BISECT_LOG"):
        if git_path(root, marker).exists():
            raise ValueError("Finish the active Git merge, rebase, cherry-pick, revert or bisect before switching.")
    worktree = None
    for line in git(root, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            worktree = Path(line.removeprefix("worktree ")).resolve()
        if line == f"branch {target}" and worktree != root:
            raise ValueError("The target branch is already checked out in another worktree.")

    launchers = [f"src/{APP_SCRIPTS[name][0]}/{APP_SCRIPTS[name][1]}" for name in app_names]
    required = [*HELPER_FILES, *launchers]
    entries = {}
    for entry in git(root, "ls-tree", "-r", "-z", target, "--", *required, *ENV_FILES).stdout.split("\0"):
        if entry:
            metadata, path = entry.split("\t", 1)
            entries[path] = metadata.split()[0]
    if any(path in entries for path in ENV_FILES):
        raise ValueError("The target tracks a component .env file. Keep local connection settings untracked before switching.")
    if any(entries.get(path) != ("100755" if path.endswith(".sh") else "100644") for path in required):
        raise ValueError("The target needs the database-switching helpers and standard executable launchers. Rebase older branches first.")


class BranchAssociations:
    """Persist local branch/database choices only after both selections succeed."""

    def __init__(self, root: Path):
        self.path = git_path(root, "taranis-dev/branches.json")
        if self.path.is_symlink():
            raise ValueError("The branch association file must be a regular local file.")
        self.original = self.path.read_bytes() if self.path.exists() else None
        try:
            self.branches = json.loads(self.original) if self.original is not None else {}
            if not isinstance(self.branches, dict) or any(not isinstance(branch, str) for branch in self.branches):
                raise ValueError
            for name in self.branches.values():
                if not isinstance(name, str):
                    raise TypeError
                database_name(name)
        except (ValueError, TypeError):
            raise ValueError("The local branch association file is invalid. Repair it before switching.") from None
        self.prepared: Path | None = None

    def database(self, branch: str, explicit: str | None) -> str:
        if explicit:
            return explicit
        if branch not in self.branches:
            raise ValueError("This branch has no database association. Choose an existing database with --db, or add --from to clone one.")
        return self.branches[branch]

    def prepare(self, branch: str, database: str):
        associations = self.branches | {branch: database}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=".branches-", mode="w", encoding="utf-8", delete=False) as staged:
            self.prepared = Path(staged.name)
            json.dump(associations, staged, indent=2, sort_keys=True)
            staged.write("\n")
            staged.flush()
            os.fsync(staged.fileno())

    def apply(self):
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self.original:
            raise RuntimeError("Branch associations changed during switching. Inspect the local association file before retrying.")
        if self.prepared is None:
            raise RuntimeError("Prepare the branch association before changing the checkout.")
        self.prepared.replace(self.path)

    def close(self):
        if self.prepared:
            self.prepared.unlink(missing_ok=True)


def require_destination(connection, config: DevelopmentConfig, database: str, source: str | None):
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,)).fetchone()
    if source:
        if exists:
            raise ValueError("The destination database already exists. Omit --from to reuse it; existing databases are never overwritten.")
        require_database(connection, source)
        return
    if not exists:
        raise ValueError("The selected database does not exist. Provide --db and --from to create an explicit clone.")
    require_database(connection, database)
    with psycopg.connect(**config.connection, dbname=database):
        pass


def switch_branch(args):
    root = args.root.resolve()
    if args.source and not args.database:
        raise ValueError("Cloning requires an explicit destination with --db as well as --from.")
    with ExitStack() as stack:
        lock_path = git_path(root, "taranis-dev/switch.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock = stack.enter_context(lock_path.open("a"))
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another branch/database switch is in progress. Retry when it finishes.") from None
        config = DevelopmentConfig(root)
        processes = None if args.stopped else config.processes(args.session)
        if processes:
            processes.preflight()
        app_names = set(processes.panes) & APP_SCRIPTS.keys() if processes else {"core", "frontend", "worker"}
        require_checkout(root, args.branch, app_names)
        associations = BranchAssociations(root)
        stack.callback(associations.close)
        database = associations.database(args.branch, args.database)
        connection = stack.enter_context(psycopg.connect(**config.connection, dbname="postgres", autocommit=True))
        if not connection.execute("SELECT pg_try_advisory_lock(%s)", (DATABASE_OPERATION_LOCK,)).fetchone()[0]:
            raise RuntimeError("Another database operation is in progress. Retry when it finishes.")
        require_database(connection, config.selected)
        require_destination(connection, config, database, args.source)
        clients = config.redis_clients(stack)
        associations.prepare(args.branch, database)
        selection = DatabaseSelection(config.env_path, database)
        stack.callback(selection.close)

        if processes:
            processes.stop()
        require_idle_databases(connection, [config.selected, database, *([args.source] if args.source else [])])
        git(root, "switch", "--no-guess", "--no-overwrite-ignore", "--", args.branch)
        if args.source:
            copy_database(connection, args.source, database)
        clear_redis(clients)
        selection.apply()
        associations.apply()
        try:
            if processes:
                processes.start(database)
        except BaseException:
            # Keep the target pair for recovery; restoring the old database here
            # would pair it with code that has already changed branches.
            if processes:
                processes.stop()
            clear_redis(clients)
            raise
    print("Branch and database selected. Applications remain stopped." if args.stopped else "Branch and database ready.")


def report_state(root: Path):
    try:
        branch = git(root, "branch", "--show-current").stdout.strip() or "(detached HEAD)"
        database = settings(root / "src/core/.env").get("DB_DATABASE", "taranis")
        print(f"Current branch: {branch}\nSelected database: {database}")
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        print("Could not read the current pair. Inspect git status and src/core/.env before restarting.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", help="existing local branch to switch to")
    parser.add_argument("--db", dest="database", type=database_name, help="explicit database association")
    parser.add_argument("--from", dest="source", type=database_name, help="clone a new database from this existing source")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--session", default="taranis", help="existing standard development tmux session")
    parser.add_argument("--stopped", action="store_true", help="all application processes are already stopped; do not restart")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        switch_branch(args)
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
    except psycopg.Error:
        print(
            "Error: PostgreSQL could not complete the operation. Check privileges, free space, active clients and connectivity.",
            file=sys.stderr,
        )
    except RedisError:
        print("Error: Development Redis could not be cleared. Inspect it before restarting applications.", file=sys.stderr)
    except (OSError, subprocess.SubprocessError):
        print("Error: The checkout or local configuration could not be updated. Inspect file permissions and Git state.", file=sys.stderr)
    except KeyboardInterrupt:
        print("Interrupted. Inspect the current branch/database pair before restarting applications.", file=sys.stderr)
    else:
        report_state(args.root)
        return 0
    report_state(args.root)
    return 1


if __name__ == "__main__":
    sys.exit(main())
