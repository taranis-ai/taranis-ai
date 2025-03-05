#!/bin/bash

set -eu

if [ ! -d ".venv" ]; then
    uv python install
    uv venv
    source .venv/bin/activate
    uv sync --all-extras
fi

source .venv/bin/activate

python ./start_dev_worker.py
