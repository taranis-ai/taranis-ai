#!/bin/bash

set -eou pipefail

cd $(git rev-parse --show-toplevel)

IMAGE_REGISTRY=${IMAGE_REGISTRY:-"ghcr.io"}
REPO_NAMESPACE=${GITHUB_REPOSITORY_OWNER:-"taranis-ai"}
REPO="${IMAGE_REGISTRY}/${REPO_NAMESPACE}"
GIT_INFO=$(./docker/git_info.sh)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD | sed 's/[^a-zA-Z0-9_.-]/_/g')

echo "Building containers for branch ${CURRENT_BRANCH} on ${REPO} with git info ${GIT_INFO}"

build_core() {
  docker buildx build --file docker/Containerfile.core \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${REPO}/taranis-core:latest" \
    --tag "${REPO}/taranis-core:${CURRENT_BRANCH}" \
    --load .
}

build_worker() {
  docker buildx build --file docker/Containerfile.worker \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${REPO}/taranis-worker:latest" \
    --tag "${REPO}/taranis-worker:${CURRENT_BRANCH}" \
    --load .
}

build_ingress() {
  docker buildx build --file docker/Containerfile.ingress \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${REPO}/taranis-ingress:latest" \
    --tag "${REPO}/taranis-ingress:${CURRENT_BRANCH}" \
    --load .
}

build_frontend() {
  docker buildx build --file docker/Containerfile.frontend \
    --build-arg git_info="${GIT_INFO}" \
    --tag "${REPO}/taranis-frontend:latest" \
    --tag "${REPO}/taranis-frontend:${CURRENT_BRANCH}" \
    --load .
}

if [[ $# -eq 0 ]]; then
  echo "No specific container specified. Building all containers..."
  build_core
  build_worker
  build_ingress
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
    ingress)
      echo "Building ingress container..."
      build_ingress
      ;;
    frontend)
      echo "Building frontend container..."
      build_frontend
      ;;
    *)
      echo "Unknown container: $1"
      echo "Usage: $0 [core|worker|ingress|frontend]"
      exit 1
      ;;
  esac
fi