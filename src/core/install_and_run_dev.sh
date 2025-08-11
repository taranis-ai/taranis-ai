#!/bin/bash

set -eu

if [ ! -d ".venv" ]; then
    uv venv
    source .venv/bin/activate
    uv pip install -e ."[dev]"
fi

source .venv/bin/activate
uv pip install -e ../models >/dev/null 2>&1

python -m flask run

