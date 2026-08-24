#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./docker/run_release_gate_tests.sh [all|postgres-tls|load]...

Runs release-gate tests against published container images.
Defaults to all gates.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(git rev-parse --show-toplevel)"
CONTAINER_CLI="${CONTAINER_CLI:-docker}"
DOCKER_IMAGE_NAMESPACE="${DOCKER_IMAGE_NAMESPACE:-ghcr.io/taranis-ai}"
TARANIS_TAG="${TARANIS_TAG:-latest}"
RUN_ID="${LOAD_RUN_ID:-${GITHUB_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-taranis-release-gate-load-$$}"
LOAD_ARTIFACT_DIR="${LOAD_ARTIFACT_DIR:-${RUNNER_TEMP:-/tmp}/taranis-release-gate/load-${RUN_ID}}"

source "$ROOT_DIR/docker/compose_command.sh"

export DOCKER_IMAGE_NAMESPACE
export TARANIS_TAG
export LOAD_ARTIFACT_DIR

resolve_compose_cmd

compose_load() {
  "${COMPOSE[@]}" \
    -f "$ROOT_DIR/docker/compose-variations/compose.load.yml" \
    --project-name "$PROJECT_NAME" \
    "$@"
}

cleanup_load() {
  status=$1
  if [[ $status -ne 0 ]]; then
    compose_load ps || true
    compose_load logs --tail=200 core frontend ingress locust || true
  fi
  compose_load down -v --remove-orphans >/dev/null 2>&1 || true
  return "$status"
}

run_postgres_tls() {
  "$ROOT_DIR/docker/test_core_postgres_tls_multiprocess.sh"
}

run_load() {
  mkdir -p "$LOAD_ARTIFACT_DIR"
  echo "Writing load-test artifacts to $LOAD_ARTIFACT_DIR"
  echo "Pulling load-test images"
  set +e
  compose_load pull database redis core frontend ingress seed locust
  status=$?
  if [[ $status -eq 0 ]]; then
    echo "Starting load-test target stack"
    compose_load up database redis core frontend ingress --pull=never --wait-timeout=300 --wait
    status=$?
  fi
  if [[ $status -eq 0 ]]; then
    echo "Seeding load-test data"
    compose_load run --rm --no-deps --pull=never seed
    status=$?
  fi
  if [[ $status -eq 0 ]]; then
    echo "Running load test"
    compose_load up locust --no-deps --pull=never --exit-code-from locust
    status=$?
  fi
  set -e
  cleanup_load "$status"
}

run_gate() {
  case "$1" in
    all)
      run_postgres_tls
      run_load
      ;;
    postgres-tls)
      run_postgres_tls
      ;;
    load)
      run_load
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown release gate: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
}

if [[ $# -eq 0 ]]; then
  set -- all
fi

for gate in "$@"; do
  run_gate "$gate"
done
