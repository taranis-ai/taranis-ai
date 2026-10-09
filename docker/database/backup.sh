#!/bin/bash
set -eou pipefail

[[ $# -eq 0 ]] || { echo "Usage: $0 (for database upgrades, see docker/README.md)" >&2; exit 1; }

backup_dir="backups/$(date +%FT%H%M%S)"
mkdir -p "${backup_dir}"

# shellcheck disable=SC1091
[[ -f .env ]] && source .env

TMP_CORE_NAME=$(docker compose ps --format '{{.Names}}' | grep core) || TMP_CORE_NAME=""
if [[ -z "$TMP_CORE_NAME" ]]; then
  echo "Error: No running 'core' service found." >&2
  exit 1
fi

docker compose exec core tar -czvf /tmp/core_data.tar.gz -C /app/data/ . > /dev/null
docker cp "${TMP_CORE_NAME}:/tmp/core_data.tar.gz" "${backup_dir}/core_data.tar.gz"
docker compose exec core rm -f /tmp/core_data.tar.gz

TMP_DB_NAME=$(docker compose ps --format '{{.Names}}' | grep database) || TMP_DB_NAME=""
if [[ -z "$TMP_DB_NAME" ]]; then
  echo "Error: No running 'database' service found." >&2
  exit 1
fi

# Database backup
docker compose exec database pg_dump -U "${DB_USER:-taranis}" --format=tar -f /tmp/database_backup.tar "${DB_DATABASE:-taranis}"

docker cp "${TMP_DB_NAME}:/tmp/database_backup.tar" "${backup_dir}/database_backup.tar"

docker compose exec database rm -f /tmp/database_backup.tar

echo "Backup created successfully in ${backup_dir}"
