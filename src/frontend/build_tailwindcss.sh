#!/bin/bash

set -euo pipefail

WATCH_MODE=${1:-}

if [ ! -x tailwindcss ]; then
  arch=$(uname -m)
  arch_short=$([ "$arch" = "x86_64" ] && echo "x64" || echo "arm64")
  curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${arch_short}
  chmod +x tailwindcss
fi

./update_assets.sh

if [ -n "$WATCH_MODE" ]; then
  ./tailwindcss -i frontend/static/css/input.css -o frontend/static/css/tailwind.css --watch
else
  ./tailwindcss -i frontend/static/css/input.css -o frontend/static/css/tailwind.css --minify
fi
