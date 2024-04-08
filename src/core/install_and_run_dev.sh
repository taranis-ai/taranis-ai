#!/bin/bash

set -eu

if [ ! -d "venv" ]; then
    uv venv venv
    source venv/bin/activate
    uv pip install -e ."[dev]"
fi

source venv/bin/activate

# Run the app
python -m flask run

