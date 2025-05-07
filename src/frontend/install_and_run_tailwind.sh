#!/bin/bash

set -eu

if [ ! -x tailwindcss ]; then
    curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
    chmod +x tailwindcss
fi

./tailwindcss -i frontend/static/css/input.css -o frontend/static/css/tailwind.css --watch

