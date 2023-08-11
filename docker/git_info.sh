#!/bin/sh

git_branch=$(git rev-parse --abbrev-ref HEAD)
git_tag=$(git describe --tags --exact-match 2>/dev/null)
if [ $? -eq 0 ]; then
    git_reference_name="TAG"
    git_reference_value="$git_tag"
else
    git_reference_name="HEAD"
    git_reference_value="$(git rev-parse --short HEAD)"
fi

printf '{"branch":"%s","%s":"%s"}\n' "$git_branch" "$git_reference_name" "$git_reference_value"
