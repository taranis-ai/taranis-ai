#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./docker/test_core_postgres_tls_multiprocess.sh

Runs a local smoke test for core with GRANIAN_WORKERS=2 and PostgreSQL TLS required.

Options:
  -h, --help   Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(git rev-parse --show-toplevel)"
CONTAINER_CLI="${CONTAINER_CLI:-docker}"
DOCKER_IMAGE_NAMESPACE="${DOCKER_IMAGE_NAMESPACE:-ghcr.io/taranis-ai}"
TARANIS_TAG="${TARANIS_TAG:-latest}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-taranis-core-tls-test-$$}"
PROBES="${TARANIS_TLS_PROBES:-30}"

source "$ROOT_DIR/docker/compose_command.sh"

export DOCKER_IMAGE_NAMESPACE
export TARANIS_TAG
export DB_DATABASE="${DB_DATABASE:-taranis}"
export DB_USER="${DB_USER:-taranis}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-taranis_tls_test}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-taranis_tls_test_jwt_secret}"
export API_KEY="${API_KEY:-taranis_tls_test_api_key}"
export BOT_API_KEY="${BOT_API_KEY:-$API_KEY}"
export PRE_SEED_PASSWORD_ADMIN="${PRE_SEED_PASSWORD_ADMIN:-admin}"
export PRE_SEED_PASSWORD_USER="${PRE_SEED_PASSWORD_USER:-user}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-}"
export DEBUG="${DEBUG:-False}"

resolve_compose_cmd

TMP_DIR="$(mktemp -d)"
export TARANIS_POSTGRES_TLS_DIR="$TMP_DIR"

compose() {
  "${COMPOSE[@]}" \
    -f "$ROOT_DIR/docker/compose.yml" \
    -f "$ROOT_DIR/docker/compose.core-postgres-tls.yml" \
    --project-name "$PROJECT_NAME" \
    "$@"
}

cleanup() {
  status=$?
  if [[ $status -ne 0 ]]; then
    compose ps || true
    compose logs --tail=200 core database || true
  fi
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
  exit "$status"
}
trap cleanup EXIT

openssl req \
  -new \
  -x509 \
  -days 1 \
  -nodes \
  -subj "/CN=database" \
  -keyout "$TMP_DIR/server.key" \
  -out "$TMP_DIR/server.crt" \
  >/dev/null 2>&1
chmod 0600 "$TMP_DIR/server.key"
chmod 0644 "$TMP_DIR/server.crt"

echo "Pulling ${DOCKER_IMAGE_NAMESPACE}/taranis-core:${TARANIS_TAG} and support images"
compose pull core database redis

echo "Starting core, database, and redis with PostgreSQL TLS required"
compose up database redis core --pull=never --wait-timeout=180 --wait

echo "Verifying non-TLS PostgreSQL TCP connections are rejected"
if compose exec -T database sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql "host=127.0.0.1 port=5432 user=$POSTGRES_USER dbname=$POSTGRES_DB sslmode=disable" -tAc "select 1" >/dev/null 2>&1'; then
  echo "PostgreSQL accepted a non-TLS TCP connection" >&2
  exit 1
fi

echo "Probing /api/health through core ${PROBES} times"
for probe in $(seq 1 "$PROBES"); do
  printf 'probe %02d/%02d: ' "$probe" "$PROBES"
  compose exec -T core python - <<'PY'
import json
import sys
import urllib.error
import urllib.request

url = "http://127.0.0.1:8080/api/health"
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        body = response.read()
except urllib.error.HTTPError as exc:
    body = exc.read()

data = json.loads(body)
services = data.get("services", {})
print(json.dumps({"database": services.get("database"), "seed_data": services.get("seed_data")}, sort_keys=True))
if services.get("database") != "up" or services.get("seed_data") != "up":
    print(json.dumps(data, sort_keys=True), file=sys.stderr)
    sys.exit(1)
PY
done

ssl_count="$(
  compose exec -T database sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from pg_stat_activity a join pg_stat_ssl s using (pid) where a.datname = current_database() and a.usename = current_user and a.client_addr is not null and s.ssl"' \
    | tr -d '[:space:]'
)"
if [[ "${ssl_count:-0}" -lt 1 ]]; then
  echo "No SSL database connections from core were visible in pg_stat_ssl" >&2
  exit 1
fi
if [[ "$ssl_count" -lt 2 ]]; then
  echo "Only $ssl_count SSL core database connection was visible; repeated probes may have hit one worker"
else
  echo "$ssl_count SSL core database connections visible"
fi

if compose logs core 2>&1 | grep -Eiq "SSL error|bad record mac|OperationalError|Unexpected exit from worker"; then
  echo "Core logs contain a TLS or worker startup failure" >&2
  exit 1
fi

echo "PASS: core stayed healthy with GRANIAN_WORKERS=2 and PostgreSQL TLS required"
