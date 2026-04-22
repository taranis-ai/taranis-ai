#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/tests/load/docker-compose.load.yml"
ARTIFACTS_ROOT="$ROOT_DIR/tests/load/artifacts"
REPORT_SERVER_HOST="127.0.0.1"
REPORT_SERVER_START_PORT="${LOAD_TEST_REPORT_PORT:-18081}"
REPORT_SERVER_PORT_FILE="$ARTIFACTS_ROOT/.report-server.port"
REPORT_SERVER_PID_FILE="$ARTIFACTS_ROOT/.report-server.pid"
REPORT_SERVER_LOG="$ARTIFACTS_ROOT/.report-server.log"
REPORT_SERVER_PORT=""
REPORT_URL=""

PROFILE="smoke"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
RUN_ID="${LOAD_RUN_ID:-load-$(date +%Y%m%d-%H%M%S)}"
ARTIFACT_DIR="${LOAD_ARTIFACT_DIR:-$ARTIFACTS_ROOT/$RUN_ID}"
INGRESS_PORT="${LOAD_TEST_INGRESS_PORT:-18080}"
PROJECT_NAME="taranis-load-${RUN_ID//[^a-zA-Z0-9]/}"
PROJECT_NAME="$(printf '%s' "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')"
LATEST_ARTIFACT_LINK="$ARTIFACTS_ROOT/latest"

usage() {
  cat <<'EOF'
Usage: ./dev/run_e2e_load_tests.sh [--profile smoke|browser_load] [--users N] [--spawn-rate N] [--run-time 2m] [--report-port N]
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
    --report-port)
      REPORT_SERVER_START_PORT="$2"
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
mkdir -p "$ARTIFACTS_ROOT"

update_latest_artifacts() {
  if [[ -f "$ARTIFACT_DIR/locust-report.html" ]]; then
    ln -sfn "$ARTIFACT_DIR" "$LATEST_ARTIFACT_LINK"
  fi
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

port_is_available() {
  python3 - "$REPORT_SERVER_HOST" "$1" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        raise SystemExit(1)
PY
}

running_report_server_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

ensure_report_server() {
  local existing_pid=""
  local existing_port=""
  local existing_command=""

  if [[ -f "$REPORT_SERVER_PID_FILE" && -f "$REPORT_SERVER_PORT_FILE" ]]; then
    existing_pid="$(<"$REPORT_SERVER_PID_FILE")"
    existing_port="$(<"$REPORT_SERVER_PORT_FILE")"
    existing_command="$(running_report_server_command "$existing_pid")"

    if [[ -n "$existing_command" && "$existing_command" == *"http.server"* && "$existing_command" == *"$ARTIFACTS_ROOT"* ]]; then
      REPORT_SERVER_PORT="$existing_port"
      REPORT_URL="http://$REPORT_SERVER_HOST:$REPORT_SERVER_PORT/latest/locust-report.html"
      return 0
    fi
  fi

  local port
  for ((port = REPORT_SERVER_START_PORT; port < REPORT_SERVER_START_PORT + 20; port++)); do
    if ! port_is_available "$port"; then
      continue
    fi

    nohup python3 -m http.server "$port" --bind "$REPORT_SERVER_HOST" --directory "$ARTIFACTS_ROOT" >"$REPORT_SERVER_LOG" 2>&1 &
    local pid=$!
    sleep 1

    if kill -0 "$pid" 2>/dev/null; then
      printf '%s\n' "$pid" >"$REPORT_SERVER_PID_FILE"
      printf '%s\n' "$port" >"$REPORT_SERVER_PORT_FILE"
      REPORT_SERVER_PORT="$port"
      REPORT_URL="http://$REPORT_SERVER_HOST:$REPORT_SERVER_PORT/latest/locust-report.html"
      return 0
    fi
  done

  return 1
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
  update_latest_artifacts
  compose down -v --remove-orphans || true
}

trap cleanup EXIT

report_server_status="unavailable"
if ensure_report_server; then
  report_server_status="http://$REPORT_SERVER_HOST:$REPORT_SERVER_PORT/"
fi

echo "Run id: $RUN_ID"
echo "Artifacts: $ARTIFACT_DIR"
echo "Latest artifacts link: $LATEST_ARTIFACT_LINK"
echo "Latest Locust report path: $LATEST_ARTIFACT_LINK/locust-report.html"
echo "Artifacts server: $report_server_status"
if [[ -n "$REPORT_URL" ]]; then
  echo "Latest Locust report URL: $REPORT_URL"
fi
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

update_latest_artifacts

if [[ -n "$REPORT_URL" ]]; then
  echo "Latest Locust report URL: $REPORT_URL"
fi
