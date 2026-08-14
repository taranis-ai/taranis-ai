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
    command -v uv >/dev/null 2>&1 || install_astral_tool uv 0.11.32 0ca8a288f44e290001c1141018c8744ecd11e7a1f98041f30ff0fdd387413286
    command -v ruff >/dev/null 2>&1 || install_astral_tool ruff 0.16.2 a5bb90974bfc98a5fa91d835fa418d536aca4bbb0872416d1cd12c8494a626ff
}

install_astral_tool() {
    local tool="$1"
    local version="$2"
    local expected_checksum="$3"
    local installer
    local actual_checksum

    installer="$(curl -LsSf "https://astral.sh/$tool/$version/install.sh")"
    if command -v sha256sum >/dev/null 2>&1; then
        actual_checksum="$(printf '%s' "$installer" | sha256sum | cut -d ' ' -f 1)"
    else
        actual_checksum="$(printf '%s' "$installer" | shasum -a 256 | cut -d ' ' -f 1)"
    fi
    if [ "$actual_checksum" != "$expected_checksum" ]; then
        echo "Checksum verification failed for $tool $version installer"
        return 1
    fi
    printf '%s' "$installer" | sh
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
    local formula
    local missing_formulas=()
    for formula in \
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
        deno; do
        brew list --formula "$formula" >/dev/null 2>&1 || missing_formulas+=("$formula")
    done

    if ((${#missing_formulas[@]})); then
        HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_INSTALL_UPGRADE=1 brew install "${missing_formulas[@]}"
    fi

    install_astral

    local nginx_config
    nginx_config="$(brew --prefix)/etc/nginx/servers/nginx.conf"
    if [ ! -f "$nginx_config" ]; then
        cp dev/nginx.conf "$nginx_config"
        nginx -t
        brew services restart nginx
    elif ! pgrep nginx >/dev/null; then
        brew services start nginx
    fi

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
