#!/usr/bin/env sh
set -e

MODULE_NAME=${MODULE_NAME:-run}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE="${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}"

if [ -f /app/gunicorn_conf.py ]; then
    DEFAULT_GUNICORN_CONF=/app/gunicorn_conf.py
elif [ -f /app/app/gunicorn_conf.py ]; then
    DEFAULT_GUNICORN_CONF=/app/app/gunicorn_conf.py
else
    DEFAULT_GUNICORN_CONF=/gunicorn_conf.py
fi
export GUNICORN_CONF="${GUNICORN_CONF:-$DEFAULT_GUNICORN_CONF}"

exec "$@"
