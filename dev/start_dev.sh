#!/bin/bash

set -eu

cd $(git rev-parse --show-toplevel)

source dev/env.dev

# Check if this is executed on ubuntu
if [ -f /etc/lsb-release ]; then
    ./dev/install_dependencies.sh
else
    echo "This script is only supported on Ubuntu."
    echo "See README.md for manual installation instructions."
    exit 1
fi

if [ ! -f "src/core/.env" ]; then
    cp dev/env.dev src/core/.env
fi

if [ ! -f "src/worker/.env" ]; then
    cp dev/env.dev src/worker/.env
fi

if [ ! -f "src/gui/.env" ]; then
    cp dev/env.dev src/gui/.env
fi

if [ ! -f "src/frontend/.env" ]; then
    cp src/frontend/env.sample src/frontend/.env
fi

echo -e "{\n  \"TARANIS_CORE_API\": \"${TARANIS_CORE_URL}\"\n}" > src/gui/public/config.local.json

docker compose -f dev/compose.yml up -d

./dev/start_tmux.sh

