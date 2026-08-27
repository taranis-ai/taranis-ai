#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

run_step() {
  printf '\n==> %s\n' "$1"
}

run_in_dir() {
  local dir="$1"
  shift
  (
    cd "$dir"
    "$@"
  )
}

sync_models() {
  run_in_dir src/models uv sync --frozen --all-extras
}

sync_core() {
  run_in_dir src/core uv sync --frozen --all-extras
}

sync_frontend() {
  run_in_dir src/frontend uv sync --frozen --all-extras
  run_in_dir src/frontend ./build_tailwindcss.sh
}

sync_worker() {
  run_in_dir src/worker uv sync --frozen --all-extras
}

run_models() {
  run_step "src/models"
  run_in_dir src/models uv run --frozen --no-sync ruff check
}

run_core() {
  run_step "src/core"
  run_in_dir src/core uv run --frozen --no-sync ruff check
  run_in_dir src/core uv run --frozen --no-sync pytest
}

run_frontend() {
  run_step "src/frontend"
  run_in_dir src/frontend uv run --frozen --no-sync ruff check
  run_in_dir src/frontend uv run --frozen --no-sync djlint --profile=jinja --check frontend/templates
  run_in_dir src/frontend uv run --frozen --no-sync pytest -p no:cacheprovider --ignore=tests/playwright
}

run_frontend_e2e_admin() {
  run_step "src/frontend e2e admin"
  run_in_dir src/frontend uv run --frozen --no-sync pytest -p no:cacheprovider --e2e-ci --e2e-stack=core \
    tests/playwright/test_e2e_admin.py -k "not test_admin_dashboard"
}

run_frontend_e2e_user() {
  run_step "src/frontend e2e user"
  run_in_dir src/frontend uv run --frozen --no-sync pytest -p no:cacheprovider --e2e-ci --e2e-stack=core \
    tests/playwright/test_e2e_user.py
}

run_frontend_e2e_support() {
  run_step "src/frontend e2e support"
  run_in_dir src/frontend uv run --frozen --no-sync pytest -p no:cacheprovider --e2e-ci --e2e-stack=full \
    tests/playwright/test_e2e_rq_tasks.py \
    tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_admin_dashboard \
    tests/playwright/test_no_javascript.py \
    tests/playwright/test_viewport_notice.py \
    tests/playwright/test_htmx_helpers.py \
    tests/playwright/test_main_js.py \
    tests/playwright/test_notification_center_js.py \
    tests/playwright/test_notification_helpers.py \
    tests/playwright/test_realtime_js.py
}

run_worker() {
  run_step "src/worker"
  run_in_dir src/worker uv run --frozen --no-sync ruff check
  run_in_dir src/worker uv run --frozen --no-sync pytest
}

start_parallel_step() {
  local name="$1"
  local command="$2"
  local log_file="$PARALLEL_LOG_DIR/${name//\//_}.log"

  printf '\n==> %s (started)\n' "$name"
  "$command" >"$log_file" 2>&1 &

  PARALLEL_NAMES+=("$name")
  PARALLEL_PIDS+=("$!")
  PARALLEL_LOGS+=("$log_file")
}

wait_parallel_steps() {
  local failed_steps=()
  local index
  local status

  for index in "${!PARALLEL_PIDS[@]}"; do
    if wait "${PARALLEL_PIDS[$index]}"; then
      printf '\n==> %s (passed)\n' "${PARALLEL_NAMES[$index]}"
    else
      status=$?
      printf '\n==> %s (failed with exit %s)\n' "${PARALLEL_NAMES[$index]}" "$status" >&2
      failed_steps+=("${PARALLEL_NAMES[$index]} (exit $status)")
    fi

    cat "${PARALLEL_LOGS[$index]}"
  done

  if [ "${#failed_steps[@]}" -ne 0 ]; then
    fail "Parallel steps failed: ${failed_steps[*]}."
  fi
}

require_command git
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "Run this command from inside the taranis-ai git worktree."
cd "$ROOT_DIR"

require_command uv

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose is required for frontend e2e tests."
fi

export DEBUG=true

PARALLEL_LOG_DIR="$(mktemp -d)"
trap 'rm -rf "$PARALLEL_LOG_DIR"' EXIT
PARALLEL_NAMES=()
PARALLEL_PIDS=()
PARALLEL_LOGS=()

start_parallel_step "sync src/models" sync_models
start_parallel_step "sync src/core" sync_core
start_parallel_step "sync src/frontend" sync_frontend
start_parallel_step "sync src/worker" sync_worker
wait_parallel_steps

PARALLEL_NAMES=()
PARALLEL_PIDS=()
PARALLEL_LOGS=()

start_parallel_step "src/models" run_models
start_parallel_step "src/core" run_core
start_parallel_step "src/frontend" run_frontend
start_parallel_step "src/worker" run_worker
start_parallel_step "src/frontend e2e admin" run_frontend_e2e_admin
start_parallel_step "src/frontend e2e user" run_frontend_e2e_user
start_parallel_step "src/frontend e2e support" run_frontend_e2e_support
wait_parallel_steps
