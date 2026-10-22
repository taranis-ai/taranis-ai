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
broker.set("rq:stale", "old database")
cache.set("cache:stale", "old database")
unrelated.set("unrelated", "retain")
invoke("switch", "feature", "--stopped")
assert selected() == "feature"
assert broker.dbsize() == cache.dbsize() == 0
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

broker.close()
cache.close()
unrelated.close()
print("Named database workflow completed successfully.")
PY
