#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! docker compose config --images | grep -Eq '^docker\.io/library/postgres:18([.-]|$)'; then
    echo "Configure the database image as PostgreSQL 18 before upgrading (check POSTGRES_TAG)." >&2
    exit 1
fi

db_container=$(docker compose ps -q database)
[[ -n "$db_container" ]] || { echo "No running database service found." >&2; exit 1; }
old_version=$(docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SHOW server_version_num"' </dev/null | tr -d '[:space:]')
[[ "$old_version" =~ ^[0-9]+$ ]] || { echo "Could not determine PostgreSQL server version." >&2; exit 1; }
old_major=$((old_version / 10000))
if (( old_major < 14 || old_major >= 18 )); then
    echo "Expected a running PostgreSQL 14-17 database; found version $old_major." >&2
    exit 1
fi

database_volume=$(docker inspect "$db_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')
[[ -n "$database_volume" ]] || { echo "Could not find the PostgreSQL data volume." >&2; exit 1; }
echo "This will back up PostgreSQL $old_major and recreate volume $database_volume for PostgreSQL 18."
read -r -p "Continue? (y/N): " confirm
[[ "$confirm" == [yY] ]] || { echo "Upgrade cancelled."; exit 1; }

docker compose pull database
service_list=$(docker compose config --services)
services=()
while IFS= read -r service; do
    [[ "$service" == database ]] || services+=("$service")
done <<< "$service_list"
docker compose stop "${services[@]}"
backup_dir=$(database/backup.sh --upgrade)
echo "Backup saved in $backup_dir"

docker compose down
docker volume rm "$database_volume"
database/restore.sh --database "$backup_dir"
docker compose up -d --wait
new_version=$(docker compose exec -T database sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SHOW server_version_num"' | tr -d '[:space:]')
[[ "$new_version" =~ ^18[0-9]{4}$ ]] || { echo "Restored database is not running PostgreSQL 18." >&2; exit 1; }
docker compose ps
echo "PostgreSQL 18 upgrade complete. Backup: $backup_dir"
