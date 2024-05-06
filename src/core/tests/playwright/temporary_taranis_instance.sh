#!/bin/bash
set -x

if [ $# -eq 0 ]; then
    echo "Usage: $0 [up|down]"
    exit 1
fi

case "$1" in
    up)
#      # DB
#      cd "$(git rev-parse --show-toplevel)/docker/dev" || echo "Error: Failed to navigate to the Docker directory.";
#      docker compose up -d database

      # GUI
      cd "$(git rev-parse --show-toplevel)/src/gui" || echo "Error: Failed to navigate to the Docker directory.";
      pwd
      npm run dev
      sleep 5

      # CORE
      cd "$(git rev-parse --show-toplevel)/src/core/tests" || echo "Error: Failed to navigate to the Docker directory.";
      source .env.e2e_extras
#        FLASK_APP=../run.py FLASK_RUN_PORT=5000 flask run &>/dev/null &
      FLASK_APP=../run.py FLASK_RUN_PORT SQLALCHEMY_DATABASE_URI flask run

      ;;
    *)
      echo "Invalid argument: $1"
      echo "Usage: $0 [up|down]"
      exit 1
      ;;
esac

set +x
