#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/tests/load/docker-compose.load.yml"

PROFILE="smoke"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
RUN_ID="${LOAD_RUN_ID:-load-$(date +%Y%m%d-%H%M%S)}"
ARTIFACT_DIR="${LOAD_ARTIFACT_DIR:-$ROOT_DIR/tests/load/artifacts/$RUN_ID}"
INGRESS_PORT="${LOAD_TEST_INGRESS_PORT:-18080}"
PROJECT_NAME="taranis-load-${RUN_ID//[^a-zA-Z0-9]/}"
PROJECT_NAME="${PROJECT_NAME,,}"

usage() {
  cat <<'EOF'
Usage: ./dev/run_load_tests.sh [--profile smoke|browser_load] [--users N] [--spawn-rate N] [--run-time 2m]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --users)
      USERS="$2"
      shift 2
      ;;
    --spawn-rate)
      SPAWN_RATE="$2"
      shift 2
      ;;
    --run-time)
      RUN_TIME="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$PROFILE" in
  smoke)
    DEFAULT_USERS="1"
    DEFAULT_SPAWN_RATE="1"
    DEFAULT_RUN_TIME="2m"
    ;;
  browser_load)
    DEFAULT_USERS="4"
    DEFAULT_SPAWN_RATE="1"
    DEFAULT_RUN_TIME="10m"
    ;;
  *)
    echo "Unsupported profile: $PROFILE" >&2
    exit 1
    ;;
esac

export LOAD_ARTIFACT_DIR="$ARTIFACT_DIR"
export LOAD_TEST_INGRESS_PORT="$INGRESS_PORT"
export LOCUST_USERS="${USERS:-$DEFAULT_USERS}"
export LOCUST_SPAWN_RATE="${SPAWN_RATE:-$DEFAULT_SPAWN_RATE}"
export LOCUST_RUN_TIME="${RUN_TIME:-$DEFAULT_RUN_TIME}"
export COMPOSE_PROJECT_NAME="$PROJECT_NAME"

mkdir -p "$ARTIFACT_DIR"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

capture_logs() {
  compose logs --no-color core frontend ingress database redis >"$ARTIFACT_DIR/compose.log" || true
  compose ps >"$ARTIFACT_DIR/compose-ps.txt" || true
}

run_and_capture() {
  local log_file="$1"
  shift

  set +e
  "$@" | tee "$log_file"
  local cmd_status=${PIPESTATUS[0]}
  set -e

  return "$cmd_status"
}

cleanup() {
  capture_logs
  compose down -v --remove-orphans || true
}

trap cleanup EXIT

echo "Run id: $RUN_ID"
echo "Artifacts: $ARTIFACT_DIR"
echo "Profile: $PROFILE"
echo "Users: $LOCUST_USERS"
echo "Spawn rate: $LOCUST_SPAWN_RATE"
echo "Run time: $LOCUST_RUN_TIME"
echo "Ingress URL: http://127.0.0.1:$LOAD_TEST_INGRESS_PORT/frontend/login"

compose build core frontend ingress seed locust check_recovery
compose up -d --wait database redis core frontend ingress

run_and_capture "$ARTIFACT_DIR/seed.log" compose run --rm seed
run_and_capture \
  "$ARTIFACT_DIR/recovery-baseline.log" \
  compose run --rm --entrypoint python check_recovery -m tests.load.load_support.check_recovery record-baseline

locust_status=0
if ! run_and_capture "$ARTIFACT_DIR/locust-console.log" compose run --rm locust; then
  locust_status=$?
fi

recovery_status=0
if ! run_and_capture "$ARTIFACT_DIR/recovery.log" compose run --rm check_recovery; then
  recovery_status=$?
fi

if [[ $locust_status -ne 0 ]]; then
  exit "$locust_status"
fi

if [[ $recovery_status -ne 0 ]]; then
  exit "$recovery_status"
fi
