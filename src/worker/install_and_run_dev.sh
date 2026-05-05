#!/bin/bash

set -eu

uv sync --all-extras --frozen --python 3.13
uv run --no-sync --frozen taranis-worker
