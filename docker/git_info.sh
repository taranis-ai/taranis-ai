#!/bin/sh

set -eu

mode=${1:-git-info}
git_branch=$(git rev-parse --abbrev-ref HEAD)
git_reference_value="$(git rev-parse --short HEAD)"
git_tag=$(git describe --tags --exact-match 2>/dev/null || true)

case "$mode" in
  git-info)
    printf '{"branch":"%s","HEAD":"%s","tag":"%s"}\n' "$git_branch" "$git_reference_value" "$git_tag"
    ;;
  build-version)
    if [ -n "$git_tag" ]; then
      printf '%s\n' "$git_tag"
    else
      printf '0.0.dev0+g%s\n' "$git_reference_value"
    fi
    ;;
  *)
    echo "Usage: $0 [git-info|build-version]" >&2
    exit 1
    ;;
esac
