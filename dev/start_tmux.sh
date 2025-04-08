#!/bin/bash

set -eu

cd $(git rev-parse --show-toplevel)

# Start a new tmux session
tmux new-session -s taranis -n core -c src/core -d
tmux send-keys -t taranis:core "./install_and_run_dev.sh" C-m

# Create GUI tab
tmux new-window -t taranis:1 -n gui -c src/gui
tmux send-keys -t taranis:gui "./install_and_run_dev.sh" C-m

# Create Worker tab
tmux new-window -t taranis:2 -n worker -c src/worker
tmux send-keys -t taranis:worker "./install_and_run_dev.sh" C-m

# Create Frontend tabs
tmux new-window -t taranis:3 -n tailwind -c src/frontend
tmux send-keys -t taranis:tailwind "./install_and_run_tailwind.sh" C-m
tmux new-window -t taranis:4 -n frontend -c src/frontend
tmux send-keys -t taranis:frontend "./install_and_run_dev.sh" C-m

# Attach to the session
tmux attach-session -t taranis

