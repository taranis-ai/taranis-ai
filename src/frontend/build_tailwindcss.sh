#!/bin/bash

set -euo pipefail

WATCH_MODE=${1:-}

if ! command -v deno >/dev/null 2>&1; then
  echo "Error: deno is not installed. Install it with: curl -fsSL https://deno.land/install.sh | sh"
  exit 1
fi

deno install --allow-scripts
deno task vendor:bundle
deno task vendor:bundle:codemirror
deno task vendor:bundle:collaboration
cp node_modules/.deno/loro-crdt@1.13.2/node_modules/loro-crdt/web/loro_wasm_bg.wasm frontend/static/vendor/loro_wasm_bg.wasm

if [ -n "$WATCH_MODE" ]; then
  deno task tw:watch
else
  deno task tw:build
fi
