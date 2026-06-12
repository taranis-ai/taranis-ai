#!/bin/bash

set -eou pipefail

cd "$(git rev-parse --show-toplevel)"

uv sync --all-extras --frozen --directory src/core
uv sync --all-extras --frozen --directory src/frontend
uv sync --all-extras --frozen --directory src/worker

cd src/frontend

uv run playwright install --with-deps --only-shell chromium

if [ ! -f "frontend/static/css/tailwind.css" ] || [ "${TARANIS_E2E_TEST_TAILWIND_REBUILD:-}" = "true" ]; then
  ./build_tailwindcss.sh
fi

uv run pytest --e2e-ci
