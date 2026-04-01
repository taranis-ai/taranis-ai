#!/bin/bash

set -euo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

source dev/env.dev

detect_platform() {
    case "$(uname -s)" in
        Darwin)
            echo "macos"
            ;;
        Linux)
            if [ -r /etc/os-release ] && grep -qi '^ID=ubuntu$' /etc/os-release; then
                echo "ubuntu"
            else
                echo "unsupported"
            fi
            ;;
        *)
            echo "unsupported"
            ;;
    esac
}

ensure_supported_platform() {
    local platform

    platform=$(detect_platform)
    if [ "$platform" = "unsupported" ]; then
        echo "This script supports Ubuntu Linux and macOS with Homebrew."
        echo "See dev/README.md for manual setup instructions."
        exit 1
    fi

    echo "$platform"
}

ensure_local_hostname() {
    if grep -Eq '^[[:space:]]*(127\.0\.0\.1|::1)[[:space:]]+([^#[:space:]]+[[:space:]]+)*local\.taranis\.ai([[:space:]]|$)' /etc/hosts; then
        return
    fi

    cat <<'EOF'
Missing local host mapping for local.taranis.ai.

Add this line to /etc/hosts and rerun ./dev/start_dev.sh:
  127.0.0.1 local.taranis.ai
EOF
    exit 1
}

ensure_nginx_config() {
    local platform=$1
    local brew_prefix
    local servers_dir
    local nginx_conf

    case "$platform" in
        ubuntu)
            if [ -f /etc/nginx/sites-enabled/local.taranis.ai ] || [ -f /etc/nginx/conf.d/local.taranis.ai.conf ]; then
                return
            fi

            cat <<'EOF'
Missing nginx configuration for local.taranis.ai.

Supported Ubuntu setups:
  sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
  sudo ln -s /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
  sudo nginx -t && sudo systemctl restart nginx

Or:
  sudo cp dev/nginx.conf /etc/nginx/conf.d/local.taranis.ai.conf
  sudo nginx -t && sudo systemctl restart nginx
EOF
            exit 1
            ;;
        macos)
            brew_prefix=$(brew --prefix)
            servers_dir="$brew_prefix/etc/nginx/servers"
            nginx_conf="$servers_dir/local.taranis.ai.conf"

            if [ -f "$nginx_conf" ]; then
                return
            fi

            cat <<EOF
Missing nginx configuration for local.taranis.ai.

Supported macOS setup with Homebrew nginx:
  mkdir -p "$servers_dir"
  cp dev/nginx.conf "$nginx_conf"
  sudo ./dev/manage_macos_nginx.sh

Homebrew nginx must be started manually with sudo because dev/nginx.conf listens on port 80.
EOF
            exit 1
            ;;
    esac
}

ensure_docker_running() {
    local platform=$1

    if ! command -v docker >/dev/null 2>&1; then
        if [ "$platform" = "macos" ]; then
            echo "Docker CLI is not available. Start Docker Desktop, Colima, or another Docker-compatible daemon first."
        else
            echo "Docker is not installed. Rerun ./dev/start_dev.sh after installing dependencies."
        fi
        exit 1
    fi

    if docker info >/dev/null 2>&1; then
        if docker compose version >/dev/null 2>&1; then
            return
        fi

        if [ "$platform" = "macos" ]; then
            echo "The Docker CLI is available, but 'docker compose' is not. Use Docker Desktop, Colima, or another Docker-compatible setup that provides 'docker compose'."
        else
            echo "The Docker CLI is available, but 'docker compose' is not. Install the Docker Compose plugin and rerun ./dev/start_dev.sh."
        fi
        exit 1
    fi

    if [ "$platform" = "macos" ]; then
        echo "Docker daemon is not reachable. Start Docker Desktop, Colima, or another Docker-compatible daemon and rerun ./dev/start_dev.sh."
    else
        echo "Docker daemon is not reachable. Ensure Docker is running and your user can access it without sudo, then rerun ./dev/start_dev.sh."
    fi
    exit 1
}

ensure_env_files() {
    if [ ! -f "src/core/.env" ]; then
        cp dev/env.dev src/core/.env
        echo "FLASK_RUN_PORT=5001" >> src/core/.env
    fi

    if [ ! -f "src/worker/.env" ]; then
        cp dev/env.dev src/worker/.env
    fi

    if [ ! -f "src/frontend/.env" ]; then
        cp dev/env.dev src/frontend/.env
        echo "FLASK_RUN_PORT=5002" >> src/frontend/.env
    fi
}

main() {
    local platform

    platform=$(ensure_supported_platform)

    ./dev/install_dependencies.sh

    ensure_docker_running "$platform"
    ensure_local_hostname
    ensure_nginx_config "$platform"
    ensure_env_files

    docker compose -f dev/compose.yml up -d
    ./dev/start_tmux.sh
}

main
