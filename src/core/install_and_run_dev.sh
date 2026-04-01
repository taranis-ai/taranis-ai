#!/bin/bash

set -euo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
LIBPQ_WRAPPER="$ROOT_DIR/dev/run_with_macos_libpq.sh"

run_with_macos_libpq() {
    "$LIBPQ_WRAPPER" "$@"
}

run_with_macos_libpq uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
run_with_macos_libpq uv pip install -e ../models
run_with_macos_libpq uv run --no-sync --frozen python -m flask run
