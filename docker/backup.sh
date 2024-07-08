#!/bin/bash
set -e

backup_dir="backups/$(date +%FT%H%M%S)"

mkdir -p "${backup_dir}"

[[ -f .env ]] && source .env
export TMP_CORE_NAME=$(docker compose ps -f '{{.Names}}' | grep core || exit "Error: No running services found.")
export TMP_DB_NAME=$(docker compose ps -f '{{.Names}}' | grep database || exit "Error: No running services found.")

docker compose exec core     tar -czvf /tmp/core_data.tar.gz -C /app/data/ .                > /dev/null
docker cp "${TMP_CORE_NAME}:/tmp/core_data.tar.gz" "${backup_dir}/core_data.tar.gz"
docker compose exec core     rm -f /tmp/core_data.tar.gz
set -x
docker compose exec database pg_dump  "${DB_DATABASE:-taranis}" -U taranis --format tar      -f /tmp/database_backup.tar  
docker cp "$TMP_DB_NAME:/tmp/database_backup.tar" "${backup_dir}/database_backup.tar"
docker compose exec database rm -f /tmp/database_backup.tar
set +x