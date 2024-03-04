#!/bin/sh

git_branch=$(git rev-parse --abbrev-ref HEAD)
git_reference_value="$(git rev-parse --short HEAD)"
git_is_tag="false"
git_tag=$(git describe --tags --exact-match 2>/dev/null)
if [ $? -eq 0 ]; then
    git_is_tag="true"
fi

printf '{"branch":"%s","HEAD":"%s", "TAG":"%s"}\n' "$git_branch" "$git_reference_value" "$git_is_tag"
