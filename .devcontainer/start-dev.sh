#!/bin/bash


tmux new-session -d -s dev

# Start the Flask server in the first window (0th window is automatically created with new-session)
tmux send-keys -t dev:0 'cd core; flask run' C-m

# Create a new window for the npm dev server and run it
tmux new-window -t dev:1
tmux send-keys -t dev:1 'cd gui; npm run dev' C-m

# Create an empty third window
tmux new-window -t dev:2

# Finally, attach to the tmux session
tmux attach -t dev
