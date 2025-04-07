#!/bin/bash

set -eu

# cd $(git rev-parse --show-toplevel)

# Create tailwind tab
tmux new-window -t taranis -n tailwind2
tmux send-keys -t taranis:tailwind2 "./install_and_run_tailwind.sh" C-m

# Create frontend tab
tmux new-window -t taranis -n frontend
tmux send-keys -t taranis:frontend "./install_and_run_dev.sh" C-m
