#!/bin/bash

set -eu

# if [ ! -d tailwindcss ]; then
#     curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
#     chmod +x tailwindcss
# fi

# ./tailwindcss -i admin/static/css/input.css -o admin/static/css/tailwind.css --watch

pnpm install
pnpm run tailwind:watch

