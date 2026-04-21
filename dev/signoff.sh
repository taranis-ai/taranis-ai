#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ensure_clean_worktree() {
  if [ -n "$(git status --short --untracked-files=normal)" ]; then
    fail "$1"
  fi
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

require_command git
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "Run this command from inside the taranis-ai git worktree."
cd "$ROOT_DIR"

require_command uv
require_command gh

ensure_clean_worktree "Working tree is not clean. Commit or stash changes before running signoff."

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  fail "GitHub CLI is not authenticated for github.com. Run 'gh auth login'."
fi

if ! gh extension list | grep -Fq 'basecamp/gh-signoff'; then
  fail "gh-signoff is not installed. Run 'gh extension install basecamp/gh-signoff'."
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose is required for frontend e2e tests."
fi

export DEBUG=true

run_step "src/core"
run_in_dir src/core uv sync --frozen --all-extras
run_in_dir src/core uv run --frozen --no-sync ruff check
run_in_dir src/core uv run --frozen --no-sync pytest

run_step "src/frontend"
run_in_dir src/frontend uv sync --frozen --all-extras
run_in_dir src/frontend uv run --frozen --no-sync ruff check
run_in_dir src/frontend uv run --frozen --no-sync djlint --profile=jinja --check frontend/templates
run_in_dir src/frontend uv run --frozen --no-sync pytest

run_step "src/frontend e2e"
run_in_dir src/frontend uv run --frozen --no-sync pytest --e2e-ci

run_step "src/worker"
run_in_dir src/worker uv sync --frozen --all-extras
run_in_dir src/worker uv run --frozen --no-sync ruff check
run_in_dir src/worker uv run --frozen --no-sync pytest

ensure_clean_worktree "Working tree changed during local validation. Review the changes before running signoff."

run_step "gh signoff"
gh signoff
