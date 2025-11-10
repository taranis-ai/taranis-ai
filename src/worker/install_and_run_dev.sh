#!/bin/bash

# Deactivate any active virtual environment to avoid conflicts
if [ -n "${VIRTUAL_ENV:-}" ]; then
    unset VIRTUAL_ENV
    unset PYTHONHOME
    PATH=$(echo "$PATH" | sed -e "s|${VIRTUAL_ENV}/bin:||")
fi

set -eu

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install -e ../models

uv run python ./start_dev_worker.py
