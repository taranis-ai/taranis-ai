#!/bin/bash

set -euo pipefail

# Check if the user can escalate privileges via sudo
check_sudo_access() {
    if ! sudo -v; then
        echo "This script requires sudo access to install packages."
        exit 1
    fi
}

check_if_installed() {
    local packages=(
        git
        tmux
        curl
        ca-certificates
        build-essential
        software-properties-common
        nodejs
        docker-ce
        docker-compose-plugin
    )
    local all_installed=true

    for pkg in "${packages[@]}"; do
        if ! dpkg -s "${pkg}" &>/dev/null; then
            all_installed=false
            break
        fi
    done

    if $all_installed; then
        echo "All packages are already installed. Exiting..."
        exit 0
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
        software-properties-common \
        libpq-dev \
        clang
}

install_astral() {
    pip install ruff uv
}

# Install and setup Docker
install_docker() {
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

# Setup Node.js from Nodesource
setup_nodejs() {
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
}


main() {
    [[ -f ./docker/dev/.installed ]] && exit 0
    check_sudo_access
    check_if_installed
    update_packages
    install_basic_utils
    install_astral
    install_docker
    setup_nodejs
    touch ./docker/dev/.installed
}

# Execute the main function
main
