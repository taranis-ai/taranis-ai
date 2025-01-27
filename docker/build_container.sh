#!/bin/bash

set -eou pipefail

cd $(git rev-parse --show-toplevel)

GITHUB_REPOSITORY_OWNER=${GITHUB_REPOSITORY_OWNER:-"ghcr.io/taranis-ai"}
GIT_INFO=$(./docker/git_info.sh)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD | sed 's/[^a-zA-Z0-9_.-]/_/g')

echo "Building containers for branch ${CURRENT_BRANCH} on ${GITHUB_REPOSITORY_OWNER} with git info ${GIT_INFO}"

docker buildx build --file docker/Containerfile.core \
  --build-arg git_info="${GIT_INFO}" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-core:latest" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-core:${CURRENT_BRANCH}" \
  --load .

docker buildx build --file docker/Containerfile.worker \
  --build-arg git_info="${GIT_INFO}" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-worker:latest" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-worker:${CURRENT_BRANCH}" \
  --load .

docker buildx build --file docker/Containerfile.gui \
  --build-arg git_info="${GIT_INFO}" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-gui:latest" \
  --tag "${GITHUB_REPOSITORY_OWNER}/taranis-gui:${CURRENT_BRANCH}" \
  --load .

