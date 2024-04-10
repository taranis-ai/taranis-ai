#!/bin/bash

set -eu

if [ ! -d ".venv" ]; then
    uv venv
    source .venv/bin/activate
    uv pip install -e ."[dev]"
fi

source .venv/bin/activate

python ./start_dev_worker.py
