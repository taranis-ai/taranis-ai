#!/bin/bash

set -euo pipefail

configure_macos_libpq() {
    local libpq_prefix

    if [ "$(uname -s)" != "Darwin" ] || ! command -v brew >/dev/null 2>&1; then
        return
    fi

    libpq_prefix=$(brew --prefix libpq 2>/dev/null || true)
    if [ -z "$libpq_prefix" ] || [ ! -d "$libpq_prefix/lib" ]; then
        return
    fi

    export DYLD_LIBRARY_PATH="$libpq_prefix/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
}

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install -e ../models

configure_macos_libpq
uv run --no-sync --frozen python -m flask run
