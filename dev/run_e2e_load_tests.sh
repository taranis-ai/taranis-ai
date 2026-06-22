#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/src/frontend"
COMPOSE_FILE="$ROOT_DIR/src/frontend/tests/load/docker-compose.load.yml"
ARTIFACTS_ROOT="$ROOT_DIR/src/frontend/tests/load/artifacts"
REPORT_SERVER_HOST="127.0.0.1"
REPORT_SERVER_START_PORT="${LOAD_TEST_REPORT_PORT:-18081}"
REPORT_SERVER_PORT_FILE="$ARTIFACTS_ROOT/.report-server.port"
REPORT_SERVER_PID_FILE="$ARTIFACTS_ROOT/.report-server.pid"
REPORT_SERVER_LOG="$ARTIFACTS_ROOT/.report-server.log"
REPORT_SERVER_PORT=""
REPORT_URL=""
COMMAND="run"

PROFILE="smoke"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
FLOWS=""
DEVICE_READ_IOPS=""
DEVICE_WRITE_IOPS=""
STORY_COUNT="${LOAD_TEST_STORY_COUNT:-1000}"
SOURCE_COUNT="${LOAD_TEST_SOURCE_COUNT:-10}"
REPORT_TYPE_COUNT="${LOAD_TEST_REPORT_TYPE_COUNT:-5}"
REPORT_COUNT="${LOAD_TEST_REPORT_COUNT:-250}"
RUN_ID="${LOAD_RUN_ID:-load-$(date +%Y%m%d-%H%M%S)}"
ARTIFACT_DIR="${LOAD_ARTIFACT_DIR:-$ARTIFACTS_ROOT/$RUN_ID}"
LOCUST_STATS_PATH="$ARTIFACT_DIR/locust_stats.csv"
UX_TIMINGS_MARKDOWN_PATH="$ARTIFACT_DIR/ux-timings-summary.md"
UX_TIMINGS_JSON_PATH="$ARTIFACT_DIR/ux-timings-summary.json"
INGRESS_PORT="${LOAD_TEST_INGRESS_PORT:-18080}"
PROJECT_NAME="taranis-load-${RUN_ID//[^a-zA-Z0-9]/}"
PROJECT_NAME="$(printf '%s' "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')"
LATEST_ARTIFACT_LINK="$ARTIFACTS_ROOT/latest"
REPORT_SERVER_MODULE="tests.load.load_support.report_server"
COMPOSE_OVERRIDE_FILE="$ARTIFACT_DIR/docker-compose.database-iops.override.yml"
COMPOSE_ARGS=(-f "$COMPOSE_FILE")
LOAD_PYTHONPATH="$FRONTEND_DIR${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  cat <<'EOF'
Usage:
  ./dev/run_e2e_load_tests.sh [--profile smoke|browser_load] [--users N] [--spawn-rate N] [--run-time 2m] [--flows login,dashboard] [--report-port N] [--assess-count N] [--report-count N] [--source-count N] [--report-type-count N] [--device-read-iops /dev/sda:500] [--device-write-iops /dev/sda:500]
  ./dev/run_e2e_load_tests.sh --stop-report-server
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
    --flows)
      FLOWS="$2"
      shift 2
      ;;
    --device-read-iops)
      DEVICE_READ_IOPS="$2"
      shift 2
      ;;
    --device-read-iops=*)
      DEVICE_READ_IOPS="${1#*=}"
      shift
      ;;
    --device-write-iops)
      DEVICE_WRITE_IOPS="$2"
      shift 2
      ;;
    --device-write-iops=*)
      DEVICE_WRITE_IOPS="${1#*=}"
      shift
      ;;
    --assess-count|--story-count)
      STORY_COUNT="$2"
      shift 2
      ;;
    --report-count)
      REPORT_COUNT="$2"
      shift 2
      ;;
    --source-count)
      SOURCE_COUNT="$2"
      shift 2
      ;;
    --report-type-count)
      REPORT_TYPE_COUNT="$2"
      shift 2
      ;;
    --report-port)
      REPORT_SERVER_START_PORT="$2"
      shift 2
      ;;
    --stop-report-server)
      COMMAND="stop-report-server"
      shift
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

clear_report_server_state() {
  rm -f "$REPORT_SERVER_PID_FILE" "$REPORT_SERVER_PORT_FILE"
}

report_server_command_matches() {
  local command="$1"
  [[ -n "$command" && "$command" == *"$REPORT_SERVER_MODULE"* && "$command" == *"--bind $REPORT_SERVER_HOST"* && "$command" == *"--directory $ARTIFACTS_ROOT"* ]]
}

discover_report_server() {
  local line pid command port

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    line="${line#"${line%%[![:space:]]*}"}"

    pid="${line%% *}"
    command="${line#"$pid"}"
    command="${command#" "}"

    if ! report_server_command_matches "$command"; then
      continue
    fi

    port=""
    if [[ "$command" =~ ${REPORT_SERVER_MODULE}[[:space:]]+([0-9]+) ]]; then
      port="${BASH_REMATCH[1]}"
    fi

    printf '%s %s\n' "$pid" "$port"
    return 0
  done < <(ps -axo pid=,command= 2>/dev/null || true)

  return 1
}

report_server_matches() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  report_server_command_matches "$command"
}

resolve_report_server() {
  local existing_pid=""
  local existing_port=""
  local discovered=""

  if [[ -f "$REPORT_SERVER_PID_FILE" ]]; then
    existing_pid="$(<"$REPORT_SERVER_PID_FILE")"
  fi
  if [[ -f "$REPORT_SERVER_PORT_FILE" ]]; then
    existing_port="$(<"$REPORT_SERVER_PORT_FILE")"
  fi

  if [[ -n "$existing_pid" ]] && report_server_matches "$existing_pid"; then
    printf '%s %s\n' "$existing_pid" "$existing_port"
    return 0
  fi

  clear_report_server_state

  if ! discovered="$(discover_report_server)"; then
    return 1
  fi

  read -r existing_pid existing_port <<<"$discovered"
  printf '%s\n' "$existing_pid" >"$REPORT_SERVER_PID_FILE"
  if [[ -n "$existing_port" ]]; then
    printf '%s\n' "$existing_port" >"$REPORT_SERVER_PORT_FILE"
  fi

  printf '%s %s\n' "$existing_pid" "$existing_port"
}

stop_report_server() {
  mkdir -p "$ARTIFACTS_ROOT"

  local existing_pid=""
  local existing_port=""

  if ! read -r existing_pid existing_port < <(resolve_report_server); then
    clear_report_server_state
    echo "No matching report server process is running."
    return 0
  fi

  kill "$existing_pid"
  sleep 0.2

  if kill -0 "$existing_pid" 2>/dev/null; then
    echo "Failed to stop report server with pid $existing_pid" >&2
    return 1
  fi

  clear_report_server_state
  if [[ -n "$existing_port" ]]; then
    echo "Stopped report server on http://$REPORT_SERVER_HOST:$existing_port/"
  else
    echo "Stopped report server."
  fi
}

if [[ "$COMMAND" == "stop-report-server" ]]; then
  stop_report_server
  exit 0
fi

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
export TARANIS_LOAD_FLOWS="$FLOWS"
export SEED_STORY_COUNT="$STORY_COUNT"
export SEED_SOURCE_COUNT="$SOURCE_COUNT"
export SEED_REPORT_TYPE_COUNT="$REPORT_TYPE_COUNT"
export SEED_REPORT_COUNT="$REPORT_COUNT"

mkdir -p "$ARTIFACT_DIR"
mkdir -p "$ARTIFACTS_ROOT"

update_latest_artifacts() {
  if [[ -f "$ARTIFACT_DIR/locust-report.html" ]]; then
    ln -sfn "$ARTIFACT_DIR" "$LATEST_ARTIFACT_LINK"
  fi
}

compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

validate_iops_limit() {
  local option_name="$1"
  local value="$2"

  if [[ ! "$value" =~ ^[^:]+:[1-9][0-9]*$ ]]; then
    echo "$option_name must use PATH:RATE with a positive integer rate, got: $value" >&2
    exit 1
  fi

  local device_path="${value%%:*}"
  if [[ ! -b "$device_path" ]]; then
    echo "$option_name device path does not exist as a block device on this host: $device_path" >&2
    exit 1
  fi
}

write_compose_override() {
  if [[ -z "$DEVICE_READ_IOPS" && -z "$DEVICE_WRITE_IOPS" ]]; then
    return 0
  fi

  if [[ -n "$DEVICE_READ_IOPS" ]]; then
    validate_iops_limit "--device-read-iops" "$DEVICE_READ_IOPS"
  fi
  if [[ -n "$DEVICE_WRITE_IOPS" ]]; then
    validate_iops_limit "--device-write-iops" "$DEVICE_WRITE_IOPS"
  fi

  local read_path="${DEVICE_READ_IOPS%%:*}"
  local read_rate="${DEVICE_READ_IOPS##*:}"
  local write_path="${DEVICE_WRITE_IOPS%%:*}"
  local write_rate="${DEVICE_WRITE_IOPS##*:}"

  {
    echo "services:"
    echo "  database:"
    echo "    blkio_config:"
    if [[ -n "$DEVICE_READ_IOPS" ]]; then
      echo "      device_read_iops:"
      echo "        - path: $read_path"
      echo "          rate: $read_rate"
    fi
    if [[ -n "$DEVICE_WRITE_IOPS" ]]; then
      echo "      device_write_iops:"
      echo "        - path: $write_path"
      echo "          rate: $write_rate"
    fi
  } >"$COMPOSE_OVERRIDE_FILE"

  COMPOSE_ARGS+=(-f "$COMPOSE_OVERRIDE_FILE")
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

  if read -r existing_pid existing_port < <(resolve_report_server); then
    REPORT_SERVER_PORT="$existing_port"
    REPORT_URL="http://$REPORT_SERVER_HOST:$REPORT_SERVER_PORT/latest/locust-report.html?run=$RUN_ID"
    return 0
  fi

  local port
  for ((port = REPORT_SERVER_START_PORT; port < REPORT_SERVER_START_PORT + 20; port++)); do
    if ! port_is_available "$port"; then
      continue
    fi

    nohup env PYTHONPATH="$LOAD_PYTHONPATH" python3 -m "$REPORT_SERVER_MODULE" "$port" --bind "$REPORT_SERVER_HOST" --directory "$ARTIFACTS_ROOT" >"$REPORT_SERVER_LOG" 2>&1 &
    local pid=$!
    sleep 1

    if kill -0 "$pid" 2>/dev/null; then
      printf '%s\n' "$pid" >"$REPORT_SERVER_PID_FILE"
      printf '%s\n' "$port" >"$REPORT_SERVER_PORT_FILE"
      REPORT_SERVER_PORT="$port"
      REPORT_URL="http://$REPORT_SERVER_HOST:$REPORT_SERVER_PORT/latest/locust-report.html?run=$RUN_ID"
      return 0
    fi
  done

  return 1
}

capture_logs() {
  compose logs --no-color core frontend ingress database redis >"$ARTIFACT_DIR/compose.log" || true
  compose ps >"$ARTIFACT_DIR/compose-ps.txt" || true
}

write_missing_page_summary() {
  cat >"$UX_TIMINGS_MARKDOWN_PATH" <<EOF
# UX Timings Summary

No \`PAGE\` timing summary could be generated because \`locust_stats.csv\` was not created.
EOF
  printf '[]\n' >"$UX_TIMINGS_JSON_PATH"
  cat "$UX_TIMINGS_MARKDOWN_PATH"
}

generate_page_summary() {
  if [[ ! -f "$LOCUST_STATS_PATH" ]]; then
    write_missing_page_summary
    return 0
  fi

  PYTHONPATH="$LOAD_PYTHONPATH" python3 -m tests.load.load_support.summarize_stats \
    "$LOCUST_STATS_PATH" \
    "$UX_TIMINGS_MARKDOWN_PATH" \
    "$UX_TIMINGS_JSON_PATH"
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

write_compose_override

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
echo "Seed stories (Assess): $SEED_STORY_COUNT"
echo "Seed reports: $SEED_REPORT_COUNT"
echo "Seed sources: $SEED_SOURCE_COUNT"
echo "Seed report types: $SEED_REPORT_TYPE_COUNT"
if [[ -n "$DEVICE_READ_IOPS" ]]; then
  echo "Database device read IOPS: $DEVICE_READ_IOPS"
fi
if [[ -n "$DEVICE_WRITE_IOPS" ]]; then
  echo "Database device write IOPS: $DEVICE_WRITE_IOPS"
fi
if [[ -n "$TARANIS_LOAD_FLOWS" ]]; then
  echo "Flows: $TARANIS_LOAD_FLOWS"
else
  echo "Flows: profile defaults"
fi
echo "Ingress URL: http://127.0.0.1:$LOAD_TEST_INGRESS_PORT/frontend/login"

compose build core frontend ingress seed locust check_recovery
compose up -d --wait database redis core frontend ingress

run_and_capture "$ARTIFACT_DIR/seed.log" compose run --rm seed
run_and_capture \
  "$ARTIFACT_DIR/recovery-baseline.log" \
  compose run --rm --entrypoint python check_recovery -m tests.load.load_support.check_recovery record-baseline

if run_and_capture "$ARTIFACT_DIR/locust-console.log" compose run --rm locust; then
  locust_status=0
else
  locust_status=$?
fi

if run_and_capture "$ARTIFACT_DIR/recovery.log" compose run --rm check_recovery; then
  recovery_status=0
else
  recovery_status=$?
fi

if generate_page_summary; then
  summary_status=0
else
  summary_status=$?
fi

echo "UX timings summary path: $UX_TIMINGS_MARKDOWN_PATH"
echo "UX timings summary JSON: $UX_TIMINGS_JSON_PATH"

if [[ $locust_status -ne 0 ]]; then
  exit "$locust_status"
fi

if [[ $recovery_status -ne 0 ]]; then
  exit "$recovery_status"
fi

if [[ $summary_status -ne 0 ]]; then
  exit "$summary_status"
fi

update_latest_artifacts

if [[ -n "$REPORT_URL" ]]; then
  echo "Latest Locust report URL: $REPORT_URL"
fi
