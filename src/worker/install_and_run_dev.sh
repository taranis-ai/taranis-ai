#!/bin/bash

set -eu

if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
python -m pip install -e ."[dev]"

# Run the app
python ./start_dev_worker.py

