#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

uv run --directory src/core --frozen --no-sync pytest -q \
  tests/test_openapi_routes.py::test_declared_operation_contracts_are_executable
uv run --directory src/frontend --frozen --no-sync pytest -q \
  tests/unit/test_api_contracts.py
