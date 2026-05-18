#!/bin/bash

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"
ALPHA_ENV="${ALPHA_ENV:-$ROOT_DIR/docker/.env.stack1}"
BRAVO_ENV="${BRAVO_ENV:-$ROOT_DIR/docker/.env.stack2}"

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

print_usage() {
    cat <<'EOF'
Usage:
  ./dev/start_collaboration_demo.sh up
  ./dev/start_collaboration_demo.sh down
  ./dev/start_collaboration_demo.sh restart
  ./dev/start_collaboration_demo.sh status
  ./dev/start_collaboration_demo.sh logs [alpha|bravo]

This starts two local demo stacks:
  alpha -> http://alpha.local.taranis.ai
  bravo -> http://bravo.local.taranis.ai

Env files:
  alpha -> $ALPHA_ENV
  bravo -> $BRAVO_ENV

Required /etc/hosts entries:
  127.0.0.1 alpha.local.taranis.ai
  127.0.0.1 bravo.local.taranis.ai

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
}

bring_up() {
    run_stack "$ALPHA_ENV" up -d
    run_stack "$BRAVO_ENV" up -d
    cat <<'EOF'

Demo stacks started:
  alpha: http://alpha.local.taranis.ai/frontend
  bravo: http://bravo.local.taranis.ai/frontend

If those hostnames do not resolve yet, add them to /etc/hosts and install dev/nginx.collaboration-demo.conf.
EOF
}

bring_down() {
    run_stack "$ALPHA_ENV" down
    run_stack "$BRAVO_ENV" down
}

show_status() {
    echo "== alpha =="
    run_stack "$ALPHA_ENV" ps
    echo
    echo "== bravo =="
    run_stack "$BRAVO_ENV" ps
}

show_logs() {
    local target="${1:-all}"
    case "$target" in
        alpha)
            run_stack "$ALPHA_ENV" logs -f
            ;;
        bravo)
            run_stack "$BRAVO_ENV" logs -f
            ;;
        all)
            echo "Use 'logs alpha' or 'logs bravo'." >&2
            exit 1
            ;;
        *)
            echo "Unknown logs target: $target" >&2
            exit 1
            ;;
    esac
}

main() {
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
