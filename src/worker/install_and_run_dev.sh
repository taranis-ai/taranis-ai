#!/bin/bash

set -eu

uv sync --all-extras --dev --frozen --python 3.13 --no-install-package taranis-models
uv pip install -e ../models

uv run --no-sync --frozen python ./start_dev_worker.py
