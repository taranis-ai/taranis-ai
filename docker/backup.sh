#!/bin/bash
set -eou pipefail

backup_dir="backups/$(date +%FT%H%M%S)"

mkdir -p "${backup_dir}"

[[ -f .env ]] && source .env

TMP_CORE_NAME=$(docker compose ps --format '{{.Names}}' | grep core)
if [[ -z "$TMP_CORE_NAME" ]]; then
  echo "Error: No running services found." >&2
  exit 1
fi
export TMP_CORE_NAME

TMP_DB_NAME=$(docker compose ps --format '{{.Names}}' | grep database)
if [[ -z "$TMP_DB_NAME" ]]; then
  echo "Error: No running services found." >&2
  exit 1
fi
export TMP_DB_NAME

# Core
docker compose exec core     tar -czvf /tmp/core_data.tar.gz -C /app/data/ .                > /dev/null
if [ $? -ne 0 ]; then echo "Backup creation failed"; exit 1; fi
docker cp "${TMP_CORE_NAME}:/tmp/core_data.tar.gz" "${backup_dir}/core_data.tar.gz"
if [ $? -ne 0 ]; then echo "Copying core backup failed"; exit 1; fi
docker compose exec core     rm -f /tmp/core_data.tar.gz
if [ $? -ne 0 ]; then echo "Failed to remove temporary backup file /tmp/core_data.tar.gz"; exit 1; fi

# Database
docker compose exec database pg_dump  "${DB_DATABASE:-taranis}" -U taranis --format tar      -f /tmp/database_backup.tar
if [ $? -ne 0 ]; then echo "Database backup failed"; exit 1; fi
docker cp "$TMP_DB_NAME:/tmp/database_backup.tar" "${backup_dir}/database_backup.tar"
if [ $? -ne 0 ]; then echo "Copying database backup failed"; exit 1; fi
docker compose exec database rm -f /tmp/database_backup.tar
if [ $? -ne 0 ]; then echo "Failed to remove temporary backup file /tmp/database_backup.tar"; exit 1; fi

echo $backup_dir
