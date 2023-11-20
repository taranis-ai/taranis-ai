#!/bin/bash

cd $(git rev-parse --show-toplevel)

source docker/dev/env.dev

if [ ! -f "src/core/.env" ]; then
    cp docker/dev/env.dev src/core/.env
fi

if [ ! -f "src/worker/.env" ]; then
    cp docker/dev/env.dev src/worker/.env
fi

if [ ! -f "src/gui/.env" ]; then
    cp docker/dev/env.dev src/gui/.env
fi

echo -e "{\n  \"TARANIS_CORE_API\": \"${TARANIS_CORE_URL}\"\n}" > src/gui/public/config.local.json

docker compose -f docker/dev/compose-ci.yml up -d

# Start a new tmux session
#tmux new-session -s taranis -n core -c src/core -d
tmux send-keys -t taranis:core "./install_and_run_dev.sh" C-m

# Create GUI tab
tmux new-window -t taranis:1 -n gui -c src/gui
tmux send-keys -t taranis:gui "./install_and_run_dev.sh" C-m

# Create Worker tab
tmux new-window -t taranis:2 -n worker -c src/worker
tmux send-keys -t taranis:worker "./install_and_run_dev.sh" C-m

# Attach to the session
tmux attach-session -t taranis
