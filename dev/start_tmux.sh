#!/bin/bash

set -eu

cd "$(git rev-parse --show-toplevel)"

# Start a new tmux session
tmux new-session -s taranis -n core -c src/core -d
tmux send-keys -t taranis:core "./install_and_run_dev.sh" C-m

# Create Frontend tabs
tmux new-window -t taranis:1 -n tailwind -c src/frontend
tmux send-keys -t taranis:tailwind "./install_and_run_tailwind.sh" C-m
tmux new-window -t taranis:2 -n frontend -c src/frontend
tmux send-keys -t taranis:frontend "./install_and_run_dev.sh" C-m

# Create Worker tab
tmux new-window -t taranis:3 -n worker -c src/worker
tmux send-keys -t taranis:worker "./install_and_run_dev.sh" C-m

# Create Cron Scheduler tab
tmux new-window -t taranis:4 -n cron -c src/worker
tmux send-keys -t taranis:cron "uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models && uv pip install -e ../models && uv run --no-sync --frozen python -m worker.cron_scheduler" C-m

# Create RQ Dashboard tab
tmux new-window -t taranis:5 -n rq-dashboard -c src/worker
tmux send-keys -t taranis:rq-dashboard "uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models && uv pip install -e ../models && uv run --no-sync --frozen rq-dashboard --redis-url redis://:${REDIS_PASSWORD}@localhost:${TARANIS_REDIS_PORT:-6379}" C-m


# Attach to the session
tmux attach-session -t taranis
