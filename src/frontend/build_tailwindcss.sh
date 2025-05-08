#!/bin/bash

set -eu

cd $(git rev-parse --show-toplevel)/src/frontend

if [ ! -x tailwindcss ]; then
  arch=$(uname -m)
  arch_short=$([ "$arch" = "x86_64" ] && echo "x64" || echo "arm64")
  curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${arch_short}
  chmod +x tailwindcss
fi

./tailwindcss -i frontend/static/css/input.css -o frontend/static/css/tailwind.css

