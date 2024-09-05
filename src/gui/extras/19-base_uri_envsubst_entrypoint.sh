#!/bin/sh

PUBLIC_BASE_PATH=${TARANIS_BASE_PATH:-/}

if [ "$PUBLIC_BASE_PATH" != "/" ]; then
    PUBLIC_BASE_PATH=$(echo "$PUBLIC_BASE_PATH" | sed -e 's/^\/*//' -e 's/\/*$//')
    PUBLIC_BASE_PATH="/$PUBLIC_BASE_PATH/"
fi

sed -i "s#/__TARANIS_BASE_PATH__/#${PUBLIC_BASE_PATH}#g" /usr/share/nginx/html/index.html
sed -i "s#/__TARANIS_BASE_PATH__/#${PUBLIC_BASE_PATH}#g" /usr/share/nginx/html/assets/*
