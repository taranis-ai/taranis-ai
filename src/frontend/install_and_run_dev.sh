#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install -e ../models

.venv/bin/python -m flask run
