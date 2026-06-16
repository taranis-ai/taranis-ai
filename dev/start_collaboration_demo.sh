#!/bin/bash

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"
ALPHA_ENV="${ALPHA_ENV:-$ROOT_DIR/docker/.env.stack1}"
BRAVO_ENV="${BRAVO_ENV:-$ROOT_DIR/docker/.env.stack2}"
CHARLIE_ENV="${CHARLIE_ENV:-$ROOT_DIR/docker/.env.stack3}"

STACK_NAMES=()
STACK_ENVS=()

add_stack() {
    local name="$1"
    local env_file="$2"
    STACK_NAMES+=("$name")
    STACK_ENVS+=("$env_file")
}

initialize_stacks() {
    add_stack "alpha" "$ALPHA_ENV"
    add_stack "bravo" "$BRAVO_ENV"
    add_stack "charlie" "$CHARLIE_ENV"
}

run_stack() {
    local env_file="$1"
    shift
    local project_name
    project_name="$(env_value "$env_file" "COMPOSE_PROJECT_NAME")"
    if [ -z "$project_name" ]; then
        echo "Missing COMPOSE_PROJECT_NAME in $env_file" >&2
        exit 1
    fi
    docker compose --project-name "$project_name" --env-file "$env_file" -f "$COMPOSE_FILE" "$@"
}

env_value() {
    local env_file="$1"
    local key="$2"
    sed -n "s/^${key}=//p" "$env_file" | head -n 1
}

stack_env() {
    local name="$1"
    local index
    for index in "${!STACK_NAMES[@]}"; do
        if [ "${STACK_NAMES[$index]}" = "$name" ]; then
            echo "${STACK_ENVS[$index]}"
            return 0
        fi
    done
    return 1
}

print_usage() {
    cat <<'EOF'
Usage:
  ./dev/start_collaboration_demo.sh up
  ./dev/start_collaboration_demo.sh down
  ./dev/start_collaboration_demo.sh restart
  ./dev/start_collaboration_demo.sh status
  ./dev/start_collaboration_demo.sh logs [alpha|bravo|charlie]

This starts three local demo stacks:
  alpha -> http://alpha.local.taranis.ai
  bravo -> http://bravo.local.taranis.ai
  charlie -> http://charlie.local.taranis.ai

Env files:
  alpha -> $ALPHA_ENV
  bravo -> $BRAVO_ENV
  charlie -> $CHARLIE_ENV

Required /etc/hosts entries:
  127.0.0.1 alpha.local.taranis.ai
  127.0.0.1 bravo.local.taranis.ai
  127.0.0.1 charlie.local.taranis.ai

Required host nginx config:
  dev/nginx.collaboration-demo.conf

EOF
}

ensure_prerequisites() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "docker is required" >&2
        exit 1
    fi
    if ! docker compose version >/dev/null 2>&1; then
        echo "docker compose is required" >&2
        exit 1
    fi
    if [ ! -f "$ALPHA_ENV" ]; then
        echo "Missing alpha env file: $ALPHA_ENV" >&2
        exit 1
    fi
    if [ ! -f "$BRAVO_ENV" ]; then
        echo "Missing bravo env file: $BRAVO_ENV" >&2
        exit 1
    fi
    if [ ! -f "$CHARLIE_ENV" ]; then
        echo "Missing charlie env file: $CHARLIE_ENV" >&2
        exit 1
    fi
}

bring_up() {
    local index
    for index in "${!STACK_NAMES[@]}"; do
        run_stack "${STACK_ENVS[$index]}" up -d
    done
    cat <<'EOF'

Demo stacks started:
  alpha: http://alpha.local.taranis.ai/frontend
  bravo: http://bravo.local.taranis.ai/frontend
  charlie: http://charlie.local.taranis.ai/frontend

If those hostnames do not resolve yet, add them to /etc/hosts and install dev/nginx.collaboration-demo.conf.
EOF
}

bring_down() {
    local index
    for index in "${!STACK_NAMES[@]}"; do
        run_stack "${STACK_ENVS[$index]}" down
    done
}

show_status() {
    local index
    for index in "${!STACK_NAMES[@]}"; do
        echo "== ${STACK_NAMES[$index]} =="
        run_stack "${STACK_ENVS[$index]}" ps
        echo
    done
}

show_logs() {
    local target="${1:-all}"
    case "$target" in
        all)
            echo "Use 'logs alpha', 'logs bravo', or 'logs charlie'." >&2
            exit 1
            ;;
        *)
            if env_file="$(stack_env "$target")"; then
                run_stack "$env_file" logs -f
            else
                echo "Unknown logs target: $target" >&2
                exit 1
            fi
    esac
}

main() {
    initialize_stacks
    ensure_prerequisites
    cd "$ROOT_DIR"

    local command="${1:-}"
    case "$command" in
        up)
            bring_up
            ;;
        down)
            bring_down
            ;;
        restart)
            bring_down
            bring_up
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-all}"
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
