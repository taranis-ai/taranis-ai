#!/bin/sh

PUBLIC_BASE_PATH=${TARANIS_BASE_PATH:-/}

if [ "$PUBLIC_BASE_PATH" != "/" ]; then
    PUBLIC_BASE_PATH="/$(echo "$PUBLIC_BASE_PATH" | sed 's|^/*||; s|/*$||')/"
fi

export TARANIS_BASE_PATH=$PUBLIC_BASE_PATH

echo "Setting base path to: $TARANIS_BASE_PATH"

envsubst "$(printf '${%s} ' $(env | cut -d'=' -f1))" < /etc/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
