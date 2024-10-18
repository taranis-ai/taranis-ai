#!/bin/bash
set -euo pipefail

DB_NAME=$(docker compose ps --format '{{.Names}}' | grep database) || { echo "Could not find service 'database'" >&2; exit 1; }
docker exec "$DB_NAME" /bin/bash -c "psql --version " | grep -q "psql (PostgreSQL) 14.*" || { echo "PostgreSQL database version is not of major version 14" >&2; exit 1; }
backup_dir=$(./backup.sh --upgrade)
docker compose down core gui && \
docker compose down database --volumes && \
./restore.sh --database "$backup_dir" && \
docker compose up -d

