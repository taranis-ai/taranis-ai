#!/bin/bash

set -eu

# Create tailwind tab
tmux new-window -t taranis -n tailwind
tmux send-keys -t taranis:tailwind "./install_and_run_tailwind.sh" C-m

# Create frontend tab
tmux new-window -t taranis -n frontend
tmux send-keys -t taranis:frontend "./install_and_run_dev.sh" C-m
