#!/bin/sh

git_branch=$(git rev-parse --abbrev-ref HEAD)
git_reference_value="$(git rev-parse --short HEAD)"
git_tag=$(git describe --tags --exact-match 2>/dev/null || true)

printf '{"branch":"%s","HEAD":"%s","tag":"%s"}\n' "$git_branch" "$git_reference_value" "$git_tag"
