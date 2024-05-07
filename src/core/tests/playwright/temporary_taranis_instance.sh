#!/bin/bash
set -x

if [ $# -eq 0 ]; then
    echo "Usage: $0 [up|down]"
    exit 1
fi

case "$1" in
    up)
      # GUI
      cd "$(git rev-parse --show-toplevel)/src/gui" || echo "Error: Failed to navigate to the GUI directory.";
      npm run dev &>/dev/null &

      # CORE
      cd "$(git rev-parse --show-toplevel)/src/core/tests" || echo "Error: Failed to navigate to the test directory.";
      FLASK_APP=../run.py flask run &>/dev/null &
      sleep 5
      ;;
    down)
      # Cleanup
        cleanup() {
        echo "Cleaning up background jobs:"
        kill $(jobs -p)
        echo "All background jobs have been terminated."
        }

        trap cleanup EXIT
      ;;
    *)
      echo "Invalid argument: $1"
      echo "Usage: $0 [up|down]"
      exit 1
      ;;
esac

set +x
