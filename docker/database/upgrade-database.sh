#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -gt 1 ]]; then
    echo "Usage: $0 [existing_database_volume] (run from your Compose deployment directory)" >&2
    exit 1
fi
database_volume=${1:-}
if [[ -z "$database_volume" ]]; then
    database_volume=$(docker compose config --format json | jq -er '.volumes.database_data.name')
fi
upgrade_image=${UPGRADE_IMAGE:-pgautoupgrade/pgautoupgrade:18-alpine}

database_image=$(docker compose config --images database)
if ! grep -Eq '^(docker\.io/)?(library/)?postgres:18([.@-]|$)' <<< "$database_image"; then
    echo "Configure the Compose database image as PostgreSQL 18 before upgrading." >&2
    exit 1
fi
docker volume inspect "$database_volume" >/dev/null
old_major=$(docker run --rm --network none \
    --mount "type=volume,src=$database_volume,dst=/data,readonly" busybox cat /data/PG_VERSION)
[[ "$old_major" =~ ^(14|15|16|17)$ ]] || { echo "Expected a PostgreSQL 14-17 cluster." >&2; exit 1; }

echo "Upgrade PostgreSQL $old_major in volume $database_volume to 18; the stack will be stopped and backed up."
read -r -p "Continue? (y/N): " confirm
[[ "$confirm" == [yY] ]] || { echo "Upgrade cancelled."; exit 1; }

docker pull "$upgrade_image"
docker compose pull database
mkdir -p backups
backup_dir=$(mktemp -d "$PWD/backups/postgres-before-18.XXXXXX")
backup_file="$backup_dir/database.tar.gz"

docker compose down
echo "Backing up to $backup_file"
docker run --rm --network none \
    --mount "type=volume,src=$database_volume,dst=/data,readonly" \
    busybox tar -czf - -C /data . > "$backup_file"
gzip -t "$backup_file"
trap 'echo "Upgrade failed. Keep the backup for recovery: $backup_file" >&2' ERR

echo "Upgrading with $upgrade_image"
docker run --rm --network none \
    --mount "type=volume,src=$database_volume,dst=/var/lib/postgresql" \
    -e PGAUTO_ONESHOT=yes \
    -e POSTGRES_USER="${DB_USER:-taranis}" -e POSTGRES_DB="${DB_DATABASE:-taranis}" \
    -e POSTGRES_PASSWORD=unused "$upgrade_image"
docker compose up -d --wait
new_version=$(docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SHOW server_version_num"' | tr -d '[:space:]')
[[ "$new_version" =~ ^18[0-9]{4}$ ]] || { echo "Database is not running PostgreSQL 18." >&2; exit 1; }
docker compose ps
echo "PostgreSQL 18 upgrade complete. Keep the backup: $backup_file"
