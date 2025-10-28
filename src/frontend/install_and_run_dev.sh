#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install -e ../models

# Set PYTHONPATH for local development to include models directory
export PYTHONPATH="../models:${PYTHONPATH:-}"

source .venv/bin/activate

python -m flask run
