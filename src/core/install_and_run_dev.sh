#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13
export COLLAB_EXTERNAL_BASE_URL="${COLLAB_EXTERNAL_BASE_URL:-http://local.taranis.ai}"
export COLLAB_CORE_API_URL="${COLLAB_CORE_API_URL:-http://127.0.0.1:${FLASK_RUN_PORT:-5001}/api}"
export COLLAB_REALTIME_HOST="${COLLAB_REALTIME_HOST:-127.0.0.1}"
uv run --no-sync --frozen taranis-collab-realtime &
collab_pid=$!
trap 'kill "$collab_pid" 2>/dev/null || true' EXIT
uv run --no-sync --frozen python -m flask run
