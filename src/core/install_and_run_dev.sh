#!/bin/bash

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
pip install -e .[dev]

# Run the app
flask run
