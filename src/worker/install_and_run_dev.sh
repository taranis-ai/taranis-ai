#!/bin/bash

set -eu

if [ ! -d ".venv" ]; then
    uv venv
    source .venv/bin/activate
    uv pip install -e ."[dev]" -e ../models
fi

source .venv/bin/activate

uv pip install -e ../models >/dev/null 2>&1

python ./start_dev_worker.py
