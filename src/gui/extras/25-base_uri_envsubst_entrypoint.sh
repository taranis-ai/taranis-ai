#!/bin/sh

PUBLIC_BASE_PATH=${TARANIS_BASE_PATH:-/}
CONFIG_FILE="/etc/nginx/conf.d/default.conf"

envsubst "${TARANIS_CORE_UPSTREAM}" < /etc/nginx/templates/default.conf.template > $CONFIG_FILE

if [ "$PUBLIC_BASE_PATH" != "/" ]; then
    PUBLIC_BASE_PATH=$(echo "$PUBLIC_BASE_PATH" | sed -e 's/^\/*//' -e 's/\/*$//')
    PUBLIC_BASE_PATH="/$PUBLIC_BASE_PATH/"
fi

sed -i "s#/__TARANIS_BASE_PATH__/#${PUBLIC_BASE_PATH}#g" /usr/share/nginx/html/index.html
sed -i "s#/__TARANIS_BASE_PATH__/#${PUBLIC_BASE_PATH}#g" /usr/share/nginx/html/assets/*

if [ "$PUBLIC_BASE_PATH" != "/" ]; then
    LOCATION_BLOCK="\n    location $PUBLIC_BASE_PATH {\n        alias /usr/share/nginx/html/;\n    }"
    grep -q "location $PUBLIC_BASE_PATH" $CONFIG_FILE || sed -i "/^}$/i \\$LOCATION_BLOCK" $CONFIG_FILE
fi
