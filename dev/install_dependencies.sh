#!/bin/bash

set -euo pipefail

# Check if the user can escalate privileges via sudo
check_sudo_access() {
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
        software-properties-common \
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
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
}

# setup local.taranis.ai
setup_nginx() {
    if [ ! -f "/etc/nginx/sites-available/local.taranis.ai" ]; then
      sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
      sudo ln -s /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
      sudo nginx -t && sudo systemctl restart nginx
    fi
}


main() {
    [[ -f ./dev/.installed ]] && exit 0
    check_sudo_access
    update_packages
    install_basic_utils
    install_astral
    install_docker
    setup_nodejs
    setup_nginx
    touch ./dev/.installed
}

# Execute the main function
main
