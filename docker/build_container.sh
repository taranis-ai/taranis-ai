#!/bin/bash

set -eou pipefail

cd $(git rev-parse --show-toplevel)

GITHUB_REPOSITORY_OWNER=${GITHUB_REPOSITORY_OWNER:-"ghcr.io/taranis-ai"}
GIT_INFO=$(./docker/git_info.sh)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD | sed 's/[^a-zA-Z0-9_.-]/_/g')

echo "Building containers for branch ${CURRENT_BRANCH} on ${GITHUB_REPOSITORY_OWNER} with git info ${GIT_INFO}"

build_core() {
  docker buildx build --file docker/Containerfile.core \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-core:latest" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-core:${CURRENT_BRANCH}" \
    --load .
}

build_worker() {
  docker buildx build --file docker/Containerfile.worker \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-worker:latest" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-worker:${CURRENT_BRANCH}" \
    --load .
}

build_gui() {
  docker buildx build --file docker/Containerfile.gui \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-gui:latest" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-gui:${CURRENT_BRANCH}" \
    --load .
}

build_frontend() {
  docker buildx build --file docker/Containerfile.frontend \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-frontend:latest" \
    --tag "${GITHUB_REPOSITORY_OWNER}/taranis-frontend:${CURRENT_BRANCH}" \
    --load .
}

if [[ $# -eq 0 ]]; then
  echo "No specific container specified. Building all containers..."
  build_core
  build_worker
  build_gui
  build_frontend
else
  case $1 in
    core)
      echo "Building core container..."
      build_core
      ;;
    worker)
      echo "Building worker container..."
      build_worker
      ;;
    gui)
      echo "Building GUI container..."
      build_gui
      ;;
    frontend)
      echo "Building frontend container..."
      build_frontend
      ;;
    *)
      echo "Unknown container: $1"
      echo "Usage: $0 [core|worker|gui|frontend]"
      exit 1
      ;;
  esac
fi