#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

cleanup() {
  local status=$?
  "$CONTAINER_CLI" rm -f -v "$PG_CONTAINER" "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
  exit "$status"
}

require_command git
require_command uv
require_command tmux
CONTAINER_CLI="${CONTAINER_CLI:-podman}"
require_command "$CONTAINER_CLI"

if [ "${CONTAINER_CLI##*/}" = "podman" ] && [ -n "${SNAP_REAL_HOME:-}" ] && [ -n "${SNAP_USER_DATA:-}" ]; then
  case "${XDG_DATA_HOME:-}" in
    "$SNAP_USER_DATA"/*) export XDG_DATA_HOME="$SNAP_REAL_HOME/.local/share" ;;
  esac
fi

ROOT_DIR="$(git rev-parse --show-toplevel)"
TMP_DIR="$(mktemp -d)"
RUN_ID="$(date +%Y%m%d%H%M%S)-$$"
PG_CONTAINER="taranis-named-db-postgres-$RUN_ID"
REDIS_CONTAINER="taranis-named-db-redis-$RUN_ID"
trap cleanup EXIT

"$CONTAINER_CLI" run --detach --name "$PG_CONTAINER" \
  -e POSTGRES_USER=taranis -e POSTGRES_PASSWORD=supersecret -e POSTGRES_DB=taranis \
  -p 127.0.0.1::5432 "${PG_IMAGE:-docker.io/library/postgres:18-alpine}" >/dev/null
"$CONTAINER_CLI" run --detach --name "$REDIS_CONTAINER" \
  -p 127.0.0.1::6379 "${REDIS_IMAGE:-docker.io/library/redis:8-alpine}" \
  redis-server --save '' --appendonly no >/dev/null

ready=false
for _ in {1..60}; do
  # Probe TCP: the PostgreSQL image also starts a temporary socket-only server.
  if "$CONTAINER_CLI" exec "$PG_CONTAINER" pg_isready -h 127.0.0.1 -U taranis -d taranis >/dev/null 2>&1 \
    && "$CONTAINER_CLI" exec "$REDIS_CONTAINER" redis-cli ping >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [ "$ready" != true ]; then
  "$CONTAINER_CLI" logs "$PG_CONTAINER" >&2 || true
  "$CONTAINER_CLI" logs "$REDIS_CONTAINER" >&2 || true
  fail "Disposable database services did not become ready."
fi

PG_PORT="$("$CONTAINER_CLI" port "$PG_CONTAINER" 5432/tcp | sed -E 's/.*:([0-9]+)$/\1/' | head -n 1)"
REDIS_PORT="$("$CONTAINER_CLI" port "$REDIS_CONTAINER" 6379/tcp | sed -E 's/.*:([0-9]+)$/\1/' | head -n 1)"
if [ -z "$PG_PORT" ] || [ -z "$REDIS_PORT" ]; then
  fail "Could not determine service ports."
fi

uv run --project "$ROOT_DIR/src/core" --frozen python - "$ROOT_DIR" "$TMP_DIR" "$PG_PORT" "$REDIS_PORT" <<'PY'
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys

from dotenv import dotenv_values
import psycopg
import redis


repo, workspace = (Path(value) for value in sys.argv[1:3])
pg_port, redis_port = sys.argv[3:]
core_env = workspace / "src/core/.env"
broker_url = f"redis://127.0.0.1:{redis_port}/0"
cache_url = f"redis://127.0.0.1:{redis_port}/1"
for component in ("core", "frontend", "worker"):
    env_file = workspace / f"src/{component}/.env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text(f"REDIS_URL={broker_url}\n", encoding="utf-8")
core_env.write_text(
    core_env.read_text(encoding="utf-8")
    + f"DB_URL=127.0.0.1:{pg_port}\nDB_USER=taranis\nDB_PASSWORD=supersecret\nDB_DATABASE=taranis\n"
    + "# Keep local settings when switching.\nAPI_KEY=local-only-value\n",
    encoding="utf-8",
)
core_env.chmod(0o600)
frontend_env = workspace / "src/frontend/.env"
frontend_env.write_text(f"REDIS_URL={broker_url}\nCACHE_REDIS_URL={cache_url}\n", encoding="utf-8")
worker_env = workspace / "src/worker/.env"
worker_env.write_text(
    f"REDIS_URL=redis://127.0.0.1:{redis_port}/3\nCACHE_REDIS_URL=redis://127.0.0.1:{redis_port}/4\n",
    encoding="utf-8",
)

# Host configuration must never redirect this isolated workflow to a developer's services.
helper_env = {
    key: value
    for key, value in os.environ.items()
    if not key.startswith(("DB_", "REDIS_", "CACHE_REDIS_", "SQLALCHEMY_")) and key not in {"TMUX", "TMUX_PANE"}
}


def invoke(*args, succeeds=True):
    result = subprocess.run(
        [sys.executable, str(repo / "dev/databases.py"), "--root", str(workspace), *args],
        env=helper_env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
    return result.stdout


def connect(database):
    return psycopg.connect(
        host="127.0.0.1", port=pg_port, user="taranis", password="supersecret", dbname=database
    )


def row(database, statement):
    with connect(database) as connection:
        return connection.execute(statement).fetchone()


def selected():
    return dotenv_values(core_env)["DB_DATABASE"]


with connect("taranis") as connection:
    connection.execute("CREATE TABLE experiment (value text NOT NULL)")
    connection.execute("INSERT INTO experiment VALUES ('original')")

original_env = core_env.read_bytes()
invoke("clone", "feature", "--stopped")
assert core_env.read_bytes() == original_env
assert row("taranis", "SELECT value FROM experiment") == ("original",)
assert row("feature", "SELECT value FROM experiment") == ("original",)

listing = invoke("list")
assert any(line.startswith("* ") and "taranis" in line for line in listing.splitlines()), listing
assert "feature" in listing, listing

broker = redis.Redis.from_url(broker_url)
cache = redis.Redis.from_url(cache_url)
unrelated = redis.Redis(host="127.0.0.1", port=redis_port, db=2)
worker_broker = redis.Redis(host="127.0.0.1", port=redis_port, db=3)
worker_cache = redis.Redis(host="127.0.0.1", port=redis_port, db=4)
broker.set("rq:stale", "old database")
cache.set("cache:stale", "old database")
unrelated.set("unrelated", "retain")
worker_broker.set("rq:worker-stale", "old database")
worker_cache.set("cache:worker-stale", "old database")
invoke("switch", "feature", "--stopped")
assert selected() == "feature"
assert broker.dbsize() == cache.dbsize() == 0
assert worker_broker.dbsize() == worker_cache.dbsize() == 0
assert unrelated.get("unrelated") == b"retain"
assert core_env.stat().st_mode & 0o777 == 0o600
assert "# Keep local settings when switching.\nAPI_KEY=local-only-value\n" in core_env.read_text(encoding="utf-8")

with connect("feature") as connection:
    connection.execute("UPDATE experiment SET value = 'feature change'")
    connection.execute("ALTER TABLE experiment ADD COLUMN branch_only integer")

invoke("switch", "taranis", "--stopped")
assert selected() == "taranis"
assert row(selected(), "SELECT * FROM experiment") == ("original",)
with connect("taranis") as connection:
    connection.execute("UPDATE experiment SET value = 'source change'")
invoke("switch", "feature", "--stopped")
assert row(selected(), "SELECT * FROM experiment") == ("feature change", None)
assert row("taranis", "SELECT * FROM experiment") == ("source change",)

previous_env = core_env.read_bytes()
invoke("clone", "taranis", "--stopped", succeeds=False)
invoke("switch", "missing", "--stopped", succeeds=False)
assert core_env.read_bytes() == previous_env
assert row("taranis", "SELECT * FROM experiment") == ("source change",)
assert row("feature", "SELECT * FROM experiment") == ("feature change", None)

broker.set("rq:pending", "retain until switching succeeds")
broker.execute_command("ACL", "SETUSER", "default", "-flushdb")
try:
    invoke("switch", "taranis", "--stopped", succeeds=False)
finally:
    broker.execute_command("ACL", "SETUSER", "default", "+flushdb")
assert core_env.read_bytes() == previous_env
assert broker.get("rq:pending") == b"retain until switching succeeds"
assert row("taranis", "SELECT * FROM experiment") == ("source change",)
assert row("feature", "SELECT * FROM experiment") == ("feature change", None)

with connect("feature") as active_connection:
    active_connection.execute("SELECT 1")
    invoke("clone", "busy_clone", "--stopped", succeeds=False)
    assert active_connection.execute("SELECT value FROM experiment").fetchone() == ("feature change",)
assert core_env.read_bytes() == previous_env
assert row("postgres", "SELECT count(*) FROM pg_database WHERE datname = 'busy_clone'") == (0,)

tmux_directory = workspace / "tmux"
tmux_directory.mkdir(mode=0o700)
helper_env["TMUX_TMPDIR"] = str(tmux_directory)
try:
    for index, component in enumerate(("core", "frontend", "worker")):
        directory = workspace / "src" / component
        launcher = directory / "install_and_run_dev.sh"
        launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$DB_DATABASE" > started-database\nexit 1\n', encoding="utf-8")
        launcher.chmod(0o700)
        command = ["tmux", "-f", "/dev/null"]
        if index == 0:
            command += ["new-session", "-d", "-s", "database-test"]
        else:
            command += ["new-window", "-t", "database-test"]
        subprocess.run(command + ["-n", component, "-c", str(directory), "/bin/sh"], env=helper_env, check=True)
    invoke("--session", "database-test", "switch", "taranis", succeeds=False)
    assert (workspace / "src/core/started-database").read_text(encoding="utf-8") == "taranis\n"
    assert core_env.read_bytes() == previous_env
    assert row("taranis", "SELECT * FROM experiment") == ("source change",)
    assert row("feature", "SELECT * FROM experiment") == ("feature change", None)
finally:
    subprocess.run(["tmux", "kill-server"], env=helper_env, capture_output=True, check=False)

# Exercise actual Git checkouts, master initialization, branch initialization,
# and disposable replacement against the same isolated PostgreSQL/Redis services.
sys.path.insert(0, str(repo / "dev"))
from database_branches import SETUP_DATABASE
from database_processes import TmuxProcesses

remote = workspace / "origin.git"
checkout = workspace / "checkout"
publisher = workspace / "publisher"
git_env = helper_env | {"GIT_LFS_SKIP_SMUDGE": "1"}


def git(directory, *arguments, succeeds=True):
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments], env=git_env,
        capture_output=True, text=True, timeout=180,
    )
    assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
    return result.stdout.strip()


subprocess.run(["git", "clone", "--bare", "--shared", str(repo), str(remote)], env=git_env, check=True, capture_output=True)
git(remote, "symbolic-ref", "HEAD", "refs/heads/master")
subprocess.run(["git", "clone", str(remote), str(checkout)], env=git_env, check=True, capture_output=True)
subprocess.run(["git", "clone", str(remote), str(publisher)], env=git_env, check=True, capture_output=True)
for directory in (checkout, publisher):
    git(directory, "config", "user.name", "Development database test")
    git(directory, "config", "user.email", "dev-database-test@example.invalid")
git(checkout, "checkout", "-b", "feature-a")
branch_migration = "src/core/migrations/20990101_01_branch-test.py"
(checkout / branch_migration).write_text(
    'from yoyo import step\nsteps = [step("CREATE TABLE branch_migration (id integer)")]\n'
)
git(checkout, "add", branch_migration)
git(checkout, "commit", "-m", "Add branch migration marker")
git(checkout, "branch", "feature-b")

for component in ("core", "frontend", "worker"):
    destination = checkout / f"src/{component}/.env"
    destination.write_bytes((workspace / f"src/{component}/.env").read_bytes())
core_env = checkout / "src/core/.env"
# The stable installed hook runs without syncing the active application's venv.
subprocess.run(["uv", "sync", "--directory", str(checkout / "src/core"), "--frozen"], env=helper_env, check=True, capture_output=True)

old_hook_calls = workspace / "existing-hook-calls"
old_hook = checkout / ".git/hooks/post-checkout"
old_hook.write_text("#!/bin/sh\nprintf '%s\\n' \"$3\" >> " + shlex.quote(str(old_hook_calls)) + "\nexit 0\n")
old_hook.chmod(0o700)


def lifecycle(*arguments, succeeds=True):
    result = subprocess.run(
        [sys.executable, str(repo / "dev/databases.py"), "--root", str(checkout), "--session", "database-test", *arguments],
        env=helper_env, capture_output=True, text=True, timeout=180,
    )
    assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
    return result.stdout


def managed_databases():
    with connect("postgres") as connection:
        return dict(connection.execute(
            "SELECT datname, shobj_description(oid, 'pg_database') FROM pg_database "
            "WHERE shobj_description(oid, 'pg_database') LIKE 'taranis-branch-databases:%'"
        ))


def template_name():
    return next(name for name, comment in managed_databases().items() if ":master:" in comment)


lifecycle("enable", "--stopped")
first_selection, first_template = selected(), template_name()
assert first_selection != "taranis"
assert row("postgres", f"SELECT datallowconn FROM pg_database WHERE datname = '{first_template}'") == (False,)
assert row(first_selection, "SELECT to_regclass('branch_migration')") == (None,)
assert row("taranis", "SELECT value FROM experiment") == ("source change",)
unrelated_worktree = workspace / "unrelated-worktree"
git(checkout, "worktree", "add", "--detach", str(unrelated_worktree), "master")
assert selected() == first_selection
git(checkout, "worktree", "remove", str(unrelated_worktree))

# A name match alone never authorizes deleting an existing database.
collision = first_selection[:-1] + "b"
with connect("postgres") as connection:
    connection.autocommit = True
    connection.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(collision)))
    lifecycle("refresh", "--stopped", succeeds=False)
    assert selected() == first_selection
    assert row("postgres", f"SELECT count(*) FROM pg_database WHERE datname = '{collision}'") == (1,)
    connection.execute(psycopg.sql.SQL("DROP DATABASE {}").format(psycopg.sql.Identifier(collision)))

urls = {}
try:
    for index, component in enumerate(("core", "frontend", "worker")):
        directory = checkout / "src" / component
        setup = ""
        if component == "worker":
            command = shlex.join([sys.executable, "-c", "import time; time.sleep(300)"])
        else:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            with (directory / ".env").open("a") as environment_file:
                environment_file.write(f"\nFLASK_RUN_PORT={port}\n")
            route = "api/health" if component == "core" else "frontend/health"
            response = directory / route
            response.parent.mkdir(parents=True, exist_ok=True)
            response.write_text(
                '{"services":{"database":"up","seed_data":"up","broker":"up","workers":"up"}}'
                if component == "core" else "ready"
            )
            urls[component] = f"http://127.0.0.1:{port}/{route}"
            if component == "core":
                setup = shlex.join(["uv", "run", "--frozen", "--no-sync", "python", "-c", SETUP_DATABASE]) + "\n"
            command = shlex.join([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"])
        script = directory / "install_and_run_dev.sh"
        script.write_text("#!/bin/sh\nset -eu\n" + setup + "exec " + command + "\n")
        script.chmod(0o700)
        tmux_command = ["tmux", "-f", "/dev/null"]
        tmux_command += ["new-session", "-d", "-s", "database-test"] if index == 0 else ["new-window", "-t", "database-test"]
        subprocess.run(tmux_command + ["-n", component, "-c", str(directory), "/bin/sh"], env=helper_env, check=True)

    os.environ["TMUX_TMPDIR"] = helper_env["TMUX_TMPDIR"]
    processes = TmuxProcesses(checkout, "database-test", urls["core"], urls["frontend"])
    processes.preflight()
    processes.start(first_selection)
    assert row(first_selection, "SELECT to_regclass('branch_migration')") == ("branch_migration",)
    with connect(first_selection) as connection:
        connection.execute("CREATE TABLE branch_data (value text)")
    broker.set("rq:branch-a", "old")
    cache.set("cache:branch-a", "old")

    # Same commit, different branch names must still rotate the database.
    git(checkout, "checkout", "feature-b")
    assert selected() != first_selection
    assert first_selection not in managed_databases()
    assert template_name() == first_template
    assert row(selected(), "SELECT to_regclass('branch_data')") == (None,)
    assert row(selected(), "SELECT to_regclass('branch_migration')") == ("branch_migration",)
    assert broker.get("rq:branch-a") is cache.get("cache:branch-a") is None
    assert unrelated.get("unrelated") == b"retain"
    before_file_checkout = core_env.read_bytes()
    git(checkout, "checkout", "feature-b", "--", branch_migration)
    assert core_env.read_bytes() == before_file_checkout

    # Master has no feature helpers. The installed snapshot still performs rotation.
    git(checkout, "checkout", "master")
    assert not (checkout / "dev/database_branches.py").exists()
    assert row(selected(), "SELECT to_regclass('branch_migration')") == (None,)

    master_sql = publisher / "src/core/core/sql/fulltext_search.sql"
    master_sql.write_text(master_sql.read_text() + "\nCREATE TABLE IF NOT EXISTS master_revision (id integer);\n")
    git(publisher, "add", "src/core/core/sql/fulltext_search.sql")
    git(publisher, "commit", "-m", "Advance master template schema")
    git(publisher, "push", "origin", "master")
    git(checkout, "checkout", "feature-a")
    assert template_name() != first_template
    assert first_template not in managed_databases()
    assert row(selected(), "SELECT to_regclass('master_revision')") == ("master_revision",)
    assert row(selected(), "SELECT to_regclass('branch_migration')") == ("branch_migration",)
    assert len(managed_databases()) == 2

    # Failed master setup leaves the previous selection/template intact and apps stopped.
    previous_env = core_env.read_bytes()
    previous_databases = managed_databases()
    master_sql.write_text(master_sql.read_text() + "\nSELECT missing_template_function();\n")
    git(publisher, "add", "src/core/core/sql/fulltext_search.sql")
    git(publisher, "commit", "-m", "Break template initialization")
    git(publisher, "push", "origin", "master")
    git(checkout, "checkout", "feature-b", succeeds=False)
    assert core_env.read_bytes() == previous_env
    assert managed_databases() == previous_databases
    assert processes._idle_apps() == {"core", "frontend", "worker"}
    assert old_hook_calls.read_text().splitlines() == ["1", "1", "0", "1", "1", "1"]
    lifecycle("disable")
    git(checkout, "checkout", "master")
    assert core_env.read_bytes() == previous_env
finally:
    subprocess.run(["tmux", "kill-server"], env=helper_env, capture_output=True, check=False)

broker.close()
cache.close()
unrelated.close()
worker_broker.close()
worker_cache.close()
print("Named and automatic branch database workflows completed successfully.")
PY
