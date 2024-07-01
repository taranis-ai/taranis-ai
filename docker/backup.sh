#!/bin/bash

set -e

backup_dir="backups/$(date +%FT%H%M%S)"

mkdir -p "${backup_dir}"

export TMP_CORE_NAME=$(docker compose ps -f '{{.Names}}' | grep core || exit "Error: No running services found.")

docker compose exec core     tar -czvf /tmp/core_data.tar.gz -C /app/data/ .   > /dev/null
docker cp "${TMP_CORE_NAME}:/tmp/core_data.tar.gz" "${backup_dir}/core_data.tar.gz"
docker compose exec core     rm -f /tmp/core_data.tar.gz
docker compose exec database pg_dumpall -U taranis                             > "${backup_dir}/database_backup.sql"
