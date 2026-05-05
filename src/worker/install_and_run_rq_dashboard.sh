#!/bin/bash

set -eu

cd "$(dirname "$0")"
source ../../dev/env.dev

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install --python .venv/bin/python -e ../models

uv run --no-sync --frozen rq-dashboard --debug --redis-url "redis://localhost:${TARANIS_REDIS_PORT:-6379}"
