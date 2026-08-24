#!/bin/bash

set -euo pipefail

# Check if the user can escalate privileges via sudo
check_sudo_access() {
    if sudo -n true 2>/dev/null; then
        return
    fi

    if ! sudo -v; then
        echo "This script requires sudo access to install packages."
        exit 1
    fi
}

# Update the package lists
update_packages() {
    sudo apt-get update
}

# Install basic utilities
install_basic_utils() {
    sudo apt-get install -y \
        git \
        tmux \
        curl \
        ca-certificates \
        build-essential \
        libpq-dev \
        clang \
        nginx
}

install_astral() {
    curl -LsSf https://astral.sh/uv/install.sh | sh
    curl -LsSf https://astral.sh/ruff/install.sh | sh
}

# Install and setup Docker
install_docker() {
    . /etc/os-release
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID \
      $VERSION_CODENAME stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

setup_deno() {
    curl -fsSL https://deno.land/install.sh | sh
}

# setup local.taranis.ai
setup_nginx() {
    if [ ! -f "/etc/nginx/sites-available/local.taranis.ai" ]; then
      sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
      sudo ln -s /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
      sudo nginx -t && sudo systemctl restart nginx
    fi
}

install_macos() {
    HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_INSTALL_UPGRADE=1 brew install \
        git \
        tmux \
        curl \
        ca-certificates \
        gcc \
        libpq \
        llvm \
        nginx \
        podman \
        podman-compose \
        deno

    install_astral

    local nginx_config
    nginx_config="$(brew --prefix)/etc/nginx/servers/nginx.conf"
    if [ ! -f "$nginx_config" ]; then
        cp dev/nginx.conf "$nginx_config"
    fi
    nginx -t
    brew services start nginx

    if ! podman info >/dev/null 2>&1; then
        if podman machine inspect >/dev/null 2>&1; then
            podman machine start
        else
            podman machine init
            podman machine start
        fi
    fi
}


main() {
    local host_os
    host_os="$(uname -s)"

    if [ "$host_os" = "Darwin" ]; then
        command -v brew >/dev/null 2>&1 || {
            echo "This script requires Homebrew on macOS."
            exit 1
        }
    fi

    [[ -f ./dev/.installed ]] && exit 0

    if [ "$host_os" = "Darwin" ]; then
        install_macos
        touch ./dev/.installed
        exit 0
    fi

    check_sudo_access
    update_packages
    install_basic_utils
    install_astral
    install_docker
    setup_deno
    setup_nginx
    touch ./dev/.installed
}

# Execute the main function
main
