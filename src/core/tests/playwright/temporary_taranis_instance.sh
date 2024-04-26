#!/bin/bash
set -x


cd "$(git rev-parse --show-toplevel)" && cd docker/test || (echo "Error: Failed to navigate to the Docker directory."; exit 1)

if [ $# -eq 0 ]; then
    echo "Usage: $0 [up|down]"
    exit 1
fi

case "$1" in
    up)
        echo "Starting Docker containers: gui, core, database..."
        docker compose -f compose-link.yml -f compose-link.override.yml up gui core database sse
        wait 10
        ;;
    down)
        echo "Stopping Docker containers..."
        docker compose down --volumes
        ;;
    *)
        echo "Invalid argument: $1"
        echo "Usage: $0 [up|down]"
        exit 1
        ;;
esac

set +x