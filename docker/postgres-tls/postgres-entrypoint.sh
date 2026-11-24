#!/bin/sh
set -eu

cp /tls/server.crt /var/lib/postgresql/server.crt
cp /tls/server.key /var/lib/postgresql/server.key
chmod 0644 /var/lib/postgresql/server.crt
chmod 0600 /var/lib/postgresql/server.key
chown postgres:postgres /var/lib/postgresql/server.crt /var/lib/postgresql/server.key 2>/dev/null || true

exec docker-entrypoint.sh "$@" -c ssl=on \
    -c ssl_cert_file=/var/lib/postgresql/server.crt \
    -c ssl_key_file=/var/lib/postgresql/server.key
