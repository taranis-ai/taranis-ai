#!/bin/bash

set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <command> [args...]"
    exit 1
fi

if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    LIBPQ_PREFIX=$(brew --prefix libpq 2>/dev/null || true)

    if [ -n "$LIBPQ_PREFIX" ] && [ -d "$LIBPQ_PREFIX/lib" ]; then
        export PATH="$LIBPQ_PREFIX/bin${PATH:+:$PATH}"
        export DYLD_LIBRARY_PATH="$LIBPQ_PREFIX/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
        export PKG_CONFIG_PATH="$LIBPQ_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
    fi
fi

exec "$@"
