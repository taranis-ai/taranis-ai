#!/bin/bash

set -eu

uv sync --all-extras --frozen
uv run --no-sync --frozen python -m flask run

