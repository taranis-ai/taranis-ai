#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13

source .venv/bin/activate
python -m flask run
