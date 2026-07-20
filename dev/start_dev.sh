#!/bin/bash

set -eu

cd "$(git rev-parse --show-toplevel)"

source dev/env.dev
export COMPOSE_PROJECT_NAME TARANIS_REDIS_PORT

if [ ! -r /etc/os-release ]; then
    echo "Unable to determine the Linux distribution."
    echo "See dev/README.md for manual installation instructions."
    exit 1
fi

. /etc/os-release

case "$ID" in
    ubuntu)
        ;;
    debian)
        if [ "${VERSION_ID:-}" != "13" ]; then
            echo "This script supports Debian 13, but Debian ${VERSION_ID:-unknown} was detected."
            echo "See dev/README.md for manual installation instructions."
            exit 1
        fi
        ;;
    *)
        echo "This script is only supported on Ubuntu and Debian 13."
        echo "See dev/README.md for manual installation instructions."
        exit 1
        ;;
esac

./dev/install_dependencies.sh

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

docker compose -f dev/compose.yml up -d

./dev/start_tmux.sh
