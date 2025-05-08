#!/bin/bash

set -eu

if [ ! -d ".venv" ]; then
    uv venv
    source .venv/bin/activate
    uv pip install -e ."[dev]"
    uv pip install -e ../models
fi

source .venv/bin/activate

python -m flask run
