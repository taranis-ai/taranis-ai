#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13

source .venv/bin/activate
uv pip install -e ../models >/dev/null 2>&1

python -m flask run

