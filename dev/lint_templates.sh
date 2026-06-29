#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
uv run --directory src/frontend --frozen --all-extras djlint --profile=jinja --reformat frontend/templates
