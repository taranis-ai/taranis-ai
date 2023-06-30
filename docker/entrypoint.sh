#!/usr/bin/env sh
set -e

MODULE_NAME=${MODULE_NAME:-run}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

export GUNICORN_CONF=${GUNICORN_CONF:-/gunicorn_conf.py}

gunicorn -c "$GUNICORN_CONF" "$APP_MODULE"
