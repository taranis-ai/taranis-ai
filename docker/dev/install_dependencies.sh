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
        python3.11
        python3.11-dev
        nodejs
        docker-ce
        docker-compose-plugin
    )
    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -qw "$pkg"; then
            missing_packages+=("$pkg")
        fi
    done

    if [ ${#missing_packages[@]} -eq 0 ]; then
        echo "All basic utilities are already installed."
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
        software-properties-common
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

# Install Python 3.11
install_python() {
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-dev
}

main() {
    check_sudo_access
    check_if_installed
    update_packages
    install_basic_utils
    install_docker
    setup_nodejs
    install_python
}

# Execute the main function
main
