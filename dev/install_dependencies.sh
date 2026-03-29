#!/bin/bash

set -euo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

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

check_sudo_access() {
    if ! sudo -v; then
        echo "This script requires sudo access to install packages."
        exit 1
    fi
}

ensure_homebrew() {
    if command_exists brew; then
        return
    fi

    echo "Homebrew is required on macOS to install local development dependencies."
    echo "Install Homebrew from https://brew.sh/ and then rerun ./dev/start_dev.sh."
    exit 1
}

ensure_xcode_clt() {
    if xcode-select -p >/dev/null 2>&1; then
        return
    fi

    echo "Xcode Command Line Tools are required on macOS."
    echo "Run 'xcode-select --install' and rerun ./dev/start_dev.sh."
    exit 1
}

install_astral() {
    if ! command_exists uv; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    if ! command_exists ruff; then
        curl -LsSf https://astral.sh/ruff/install.sh | sh
    fi
}

install_deno() {
    if ! command_exists deno; then
        curl -fsSL https://deno.land/install.sh | sh
    fi
}

install_ubuntu_dependencies() {
    sudo apt-get update
    sudo apt-get install -y \
        git \
        tmux \
        curl \
        ca-certificates \
        build-essential \
        software-properties-common \
        libpq-dev \
        clang \
        nginx

    sudo mkdir -p /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    install_astral
    install_deno
}

install_macos_dependencies() {
    local packages=(
        tmux
        deno
        nginx
        libpq
    )

    brew install "${packages[@]}"
    install_astral
}

dependencies_ready() {
    local platform=$1

    case "$platform" in
        ubuntu)
            command_exists tmux &&
                command_exists docker &&
                command_exists nginx &&
                command_exists deno &&
                command_exists uv &&
                command_exists ruff
            ;;
        macos)
            command_exists brew &&
                xcode-select -p >/dev/null 2>&1 &&
                command_exists tmux &&
                command_exists deno &&
                command_exists uv &&
                command_exists ruff &&
                [ -x "$(brew --prefix)/opt/nginx/bin/nginx" ] &&
                [ -d "$(brew --prefix libpq)/lib" ]
            ;;
        *)
            return 1
            ;;
    esac
}

main() {
    local platform
    local installed_marker

    platform=$(detect_platform)
    installed_marker="$ROOT_DIR/dev/.installed.$platform"

    if [ "$platform" = "unsupported" ]; then
        echo "This script supports Ubuntu Linux and macOS with Homebrew."
        echo "See dev/README.md for manual setup instructions."
        exit 1
    fi

    if [ -f "$installed_marker" ] && dependencies_ready "$platform"; then
        exit 0
    fi

    case "$platform" in
        ubuntu)
            check_sudo_access
            install_ubuntu_dependencies
            ;;
        macos)
            ensure_homebrew
            ensure_xcode_clt
            install_macos_dependencies
            ;;
    esac

    touch "$installed_marker"
}

main
