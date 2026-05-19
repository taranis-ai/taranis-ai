#!/bin/sh

set -eu

git_tag=$(git describe --tags --exact-match 2>/dev/null || true)

if [ -n "$git_tag" ]; then
  printf '%s\n' "$git_tag"
  exit 0
fi

git_reference_value="$(git rev-parse --short HEAD)"
printf '0.0.dev0+g%s\n' "$git_reference_value"
