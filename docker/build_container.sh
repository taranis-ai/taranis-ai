#!/bin/bash

set -eou pipefail

cd "$(git rev-parse --show-toplevel)"

IMAGE_REGISTRY=${IMAGE_REGISTRY:-"ghcr.io"}
REPO_NAMESPACE=${GITHUB_REPOSITORY_OWNER:-"taranis-ai"}
REPO="${IMAGE_REGISTRY}/${REPO_NAMESPACE}"
GIT_INFO=$(./docker/git_info.sh)
BUILD_VERSION=${BUILD_VERSION:-$(./docker/build_version.sh)}
BUILDX_CACHE_MODE=${BUILDX_CACHE_MODE:-local}
BUILDX_OUTPUT=${BUILDX_OUTPUT:-load}
BUILDX_LOCAL_CACHE_ROOT=${BUILDX_LOCAL_CACHE_ROOT:-.buildx-cache}
BUILDX_REGISTRY_CACHE_SUFFIX=${BUILDX_REGISTRY_CACHE_SUFFIX:-buildcache}
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD | sed 's/[^a-zA-Z0-9_.-]/_/g')
BUILDX_DRIVER=$(docker buildx inspect --bootstrap 2>/dev/null | awk '/Driver:/ { print $2; exit }')

echo "Building containers for branch ${CURRENT_BRANCH} on ${REPO} with git info ${GIT_INFO} and build version ${BUILD_VERSION}"

build_image() {
  local image_name=$1
  local containerfile=$2
  local cache_src=""
  local cache_dest=""
  local effective_cache_mode="${BUILDX_CACHE_MODE}"
  local -a cache_args=()
  local -a output_args=()
  local -a build_args=(
    --build-arg "git_info=${GIT_INFO}"
    --build-arg "build_version=${BUILD_VERSION}"
  )

  if [[ "${effective_cache_mode}" == "local" && "${BUILDX_DRIVER}" == "docker" ]]; then
    echo "Buildx driver '${BUILDX_DRIVER}' does not support local cache export; continuing without cache export."
    effective_cache_mode="none"
  fi

  if [[ "${effective_cache_mode}" == "local" ]]; then
    cache_src="${BUILDX_LOCAL_CACHE_ROOT}/${image_name}"
    cache_dest="${cache_src}-new"
    mkdir -p "${cache_src}"
    rm -rf "${cache_dest}"
    cache_args=(
      --cache-from "type=local,src=${cache_src}"
      --cache-to "type=local,dest=${cache_dest},mode=max"
    )
  elif [[ "${effective_cache_mode}" == "registry" ]]; then
    cache_args=(
      --cache-from "type=registry,ref=${REPO}/${image_name}:${BUILDX_REGISTRY_CACHE_SUFFIX}-${CURRENT_BRANCH}"
      --cache-from "type=registry,ref=${REPO}/${image_name}:${BUILDX_REGISTRY_CACHE_SUFFIX}-master"
      --cache-to "type=registry,ref=${REPO}/${image_name}:${BUILDX_REGISTRY_CACHE_SUFFIX}-${CURRENT_BRANCH},mode=max"
    )
  fi

  if [[ "${BUILDX_OUTPUT}" == "load" ]]; then
    output_args=(--load)
  elif [[ "${BUILDX_OUTPUT}" == "push" ]]; then
    output_args=(--push)
  else
    output_args=("--output=${BUILDX_OUTPUT}")
  fi

  docker buildx build \
    --file "${containerfile}" \
    "${build_args[@]}" \
    --tag "${REPO}/${image_name}:latest" \
    --tag "${REPO}/${image_name}:${CURRENT_BRANCH}" \
    "${cache_args[@]}" \
    "${output_args[@]}" \
    .

  if [[ "${effective_cache_mode}" == "local" ]]; then
    rm -rf "${cache_src}"
    mv "${cache_dest}" "${cache_src}"
  fi
}

build_core() {
  build_image "taranis-core" "docker/Containerfile.core"
}

build_worker() {
  build_image "taranis-worker" "docker/Containerfile.worker"
}

build_ingress() {
  build_image "taranis-ingress" "docker/Containerfile.ingress"
}

build_frontend() {
  build_image "taranis-frontend" "docker/Containerfile.frontend"
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
