#!/bin/bash

set -eu

if [ "$(uname -s)" = "Darwin" ]; then
    export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
fi

uv sync --all-extras --frozen --python 3.13
uv run --no-sync --frozen taranis-worker
