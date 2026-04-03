#!/bin/bash

set -eu

unset VIRTUAL_ENV

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install --python .venv/bin/python -e ../models

uv run --no-sync --frozen python -m worker.cron_scheduler
