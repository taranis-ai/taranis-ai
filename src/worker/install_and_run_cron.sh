#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install --python .venv/bin/python -e ../models

uv run --no-sync --frozen taranis-cron
