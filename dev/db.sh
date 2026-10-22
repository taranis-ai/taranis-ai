#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --project "$repo_root/src/core" --frozen python "$repo_root/dev/databases.py" "$@"
