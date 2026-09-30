#!/bin/bash
set -eou pipefail

UPGRADE_MODE=false
if [[ "${1:-}" == "--upgrade" ]]; then
  UPGRADE_MODE=true
  shift
fi

backup_dir="backups/$(date +%FT%H%M%S)"
mkdir -p "${backup_dir}"

# shellcheck disable=SC1091
[[ -f .env ]] && source .env

if [ "$UPGRADE_MODE" == "true" ]; then
  compose_project_name="${COMPOSE_PROJECT_NAME:-$(basename "$(pwd)")}"
  docker volume inspect "${compose_project_name}_core_data" >/dev/null
  docker run --rm -v "${compose_project_name}_core_data:/app/data:ro" busybox \
    tar -czf - -C /app/data . > "${backup_dir}/core_data.tar.gz"
else
  TMP_CORE_NAME=$(docker compose ps --format '{{.Names}}' | grep core) || TMP_CORE_NAME=""
  if [[ -z "$TMP_CORE_NAME" ]]; then
    echo "Error: No running 'core' service found." >&2
    exit 1
  fi

  docker compose exec core tar -czvf /tmp/core_data.tar.gz -C /app/data/ . > /dev/null
  docker cp "${TMP_CORE_NAME}:/tmp/core_data.tar.gz" "${backup_dir}/core_data.tar.gz"
  docker compose exec core rm -f /tmp/core_data.tar.gz
fi

TMP_DB_NAME=$(docker compose ps --format '{{.Names}}' | grep database) || TMP_DB_NAME=""
if [[ -z "$TMP_DB_NAME" ]]; then
  echo "Error: No running 'database' service found." >&2
  exit 1
fi

# Database backup
if [ "$UPGRADE_MODE" == "true" ]; then
  PG_DUMP_OPTIONS="--quote-all-identifiers"
else
  PG_DUMP_OPTIONS=""
fi

docker compose exec database pg_dump -U "${DB_USER:-taranis}" $PG_DUMP_OPTIONS --format=tar -f /tmp/database_backup.tar "${DB_DATABASE:-taranis}"

docker cp "${TMP_DB_NAME}:/tmp/database_backup.tar" "${backup_dir}/database_backup.tar"

docker compose exec database rm -f /tmp/database_backup.tar

if [ "$UPGRADE_MODE" == "true" ]; then
  echo "${backup_dir}"
else
  echo "Backup created successfully in ${backup_dir}"
fi
