#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/src/frontend"
COMPOSE_FILE="$ROOT_DIR/src/frontend/tests/load/docker-compose.load.yml"
ARTIFACTS_ROOT="$ROOT_DIR/src/frontend/tests/load/artifacts"
LATEST_ARTIFACT_LINK="$ARTIFACTS_ROOT/latest"

PROFILE="smoke"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
FLOWS=""
DEVICE_READ_IOPS=""
DEVICE_WRITE_IOPS=""
STORY_COUNT="${LOAD_TEST_STORY_COUNT:-1000}"
REPORT_COUNT="${LOAD_TEST_REPORT_COUNT:-250}"
RUN_ID="${LOAD_RUN_ID:-load-$(date +%Y%m%d-%H%M%S)}"
ARTIFACT_DIR="${LOAD_ARTIFACT_DIR:-$ARTIFACTS_ROOT/$RUN_ID}"
INGRESS_PORT="${LOAD_TEST_INGRESS_PORT:-18080}"
PROJECT_NAME="taranis-load-${RUN_ID//[^a-zA-Z0-9]/}"
PROJECT_NAME="$(printf '%s' "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')"
LOAD_PYTHONPATH="$FRONTEND_DIR${PYTHONPATH:+:$PYTHONPATH}"
COMPOSE_OVERRIDE_FILE="$ARTIFACT_DIR/docker-compose.database-iops.override.yml"
COMPOSE_ARGS=(-f "$COMPOSE_FILE")

usage() {
  cat <<'EOF'
Usage:
  ./dev/run_e2e_load_tests.sh [--profile smoke|browser_load] [--users N] [--spawn-rate N] [--run-time 2m] [--flows login,dashboard] [--assess-count N] [--story-count N] [--report-count N] [--device-read-iops /dev/sda:500] [--device-write-iops /dev/sda:500]
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
export TARANIS_LOAD_FLOWS="$FLOWS"
export SEED_STORY_COUNT="$STORY_COUNT"
export SEED_REPORT_COUNT="$REPORT_COUNT"

mkdir -p "$ARTIFACT_DIR"

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

capture_logs() {
  compose logs --no-color core frontend ingress database redis >"$ARTIFACT_DIR/compose.log" || true
  compose ps >"$ARTIFACT_DIR/compose-ps.txt" || true
}

cleanup() {
  capture_logs
  compose down -v --remove-orphans || true
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

run_seed() {
  (
    cd "$FRONTEND_DIR/tests/load"
    DEBUG=true \
      PYTHONPATH="$LOAD_PYTHONPATH" \
      CORE_API_URL="http://127.0.0.1:$LOAD_TEST_INGRESS_PORT/api" \
      API_KEY="load_testing_api_key" \
      uv run python -m tests.load.load_support.seed
  )
}

update_latest_link() {
  if [[ -e "$LATEST_ARTIFACT_LINK" && ! -L "$LATEST_ARTIFACT_LINK" ]]; then
    echo "Skipping latest artifact link because the path exists and is not a symlink: $LATEST_ARTIFACT_LINK" >&2
    return 0
  fi

  ln -sfn "$ARTIFACT_DIR" "$LATEST_ARTIFACT_LINK"
}

write_compose_override

trap cleanup EXIT

echo "Run id: $RUN_ID"
echo "Artifacts: $ARTIFACT_DIR"
echo "Locust report: $ARTIFACT_DIR/locust-report.html"
echo "Locust stats: $ARTIFACT_DIR/locust_stats.csv"
echo "Locust console log: $ARTIFACT_DIR/locust-console.log"
echo "Profile: $PROFILE"
echo "Users: $LOCUST_USERS"
echo "Spawn rate: $LOCUST_SPAWN_RATE"
echo "Run time: $LOCUST_RUN_TIME"
echo "Seed stories (Assess): $SEED_STORY_COUNT"
echo "Seed reports: $SEED_REPORT_COUNT"
if [[ -n "$DEVICE_READ_IOPS" ]]; then
  echo "Database device read IOPS: $DEVICE_READ_IOPS"
fi
if [[ -n "$DEVICE_WRITE_IOPS" ]]; then
  echo "Database device write IOPS: $DEVICE_WRITE_IOPS"
fi
echo "Ingress URL: http://127.0.0.1:$LOAD_TEST_INGRESS_PORT/frontend/login"
if [[ -n "$TARANIS_LOAD_FLOWS" ]]; then
  echo "Flows: $TARANIS_LOAD_FLOWS"
else
  echo "Flows: profile defaults"
fi

compose build core frontend ingress locust
compose up -d --wait database redis core frontend ingress

run_and_capture "$ARTIFACT_DIR/seed.log" run_seed

if run_and_capture "$ARTIFACT_DIR/locust-console.log" compose run --rm locust; then
  locust_status=0
else
  locust_status=$?
fi

update_latest_link

echo "Latest artifacts: $LATEST_ARTIFACT_LINK"
echo "Latest Locust report: $LATEST_ARTIFACT_LINK/locust-report.html"
echo "Open latest report: file://$LATEST_ARTIFACT_LINK/locust-report.html"

if [[ $locust_status -ne 0 ]]; then
  exit "$locust_status"
fi

echo "Locust report: $ARTIFACT_DIR/locust-report.html"
echo "Locust stats: $ARTIFACT_DIR/locust_stats.csv"
