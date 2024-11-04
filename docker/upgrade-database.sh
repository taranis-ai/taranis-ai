#!/bin/bash
set -euo pipefail

echo "WARNING: This script will upgrade the database. This process may result in data loss."
echo "It is recommended to backup your data (e.g. using the 'docker/backup.sh' script or manually) before proceeding."
read -p "Are you sure you want to continue? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "Upgrade cancelled."
    exit 1
fi

DB_NAME=$(docker compose ps --format '{{.Names}}' | grep database) || { echo "Could not find service 'database'" >&2; exit 1; }
docker exec "$DB_NAME" /bin/bash -c "psql --version " | grep -q "psql (PostgreSQL) 14.*" || { echo "PostgreSQL database version is not of major version 14" >&2; exit 1; }
backup_dir=$(./backup.sh --upgrade)
docker compose down core gui && \
docker compose down database --volumes && \
./restore.sh --database "$backup_dir" && \
docker compose up -d
