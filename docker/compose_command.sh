#!/usr/bin/env bash

# shellcheck disable=SC2034
resolve_compose_cmd() {
  local container_cli="${CONTAINER_CLI:-docker}"

  if [[ -n "${COMPOSE_CMD:-}" ]]; then
    # shellcheck disable=SC2206
    COMPOSE=($COMPOSE_CMD)
  elif "$container_cli" compose version >/dev/null 2>&1; then
    COMPOSE=("$container_cli" compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    echo "Could not find docker compose. Set COMPOSE_CMD if your compose command is custom." >&2
    return 1
  fi
}
