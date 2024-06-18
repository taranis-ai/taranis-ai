#!/bin/bash

set -e

backup_dir="backups/$(date +%FT%H%M%S)"

mkdir -p "${backup_dir}"

TMP_CORE_NAME=$(docker compose ps -f  '{{.Names}}' | grep core || echo "Error: No running services found.")
export TMP_CORE_NAME
echo "Name of Core's container is: $TMP_CORE_NAME"

docker exec $TMP_CORE_NAME   tar czv /app/data      > "${backup_dir}/core_data.tar.gz"
docker compose exec database pg_dumpall -U taranis  > "${backup_dir}/database_backup.sql"

unset TMP_CORE_NAME