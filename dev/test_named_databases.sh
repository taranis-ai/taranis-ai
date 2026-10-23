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

uv run --project "$ROOT_DIR/src/core" --frozen python "$ROOT_DIR/dev/tests/named_databases.py" \
  "$ROOT_DIR" "$TMP_DIR" "$PG_PORT" "$REDIS_PORT"
