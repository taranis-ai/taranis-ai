#!/bin/bash

set -e

backup_dir="backups/$(date +%FT%H%M%S)"

mkdir -p "${backup_dir}"

docker compose exec core     tar czvf core_data.tar.gz /app/data    > "${backup_dir}/core_data.tar.gz"
docker compose exec core     rm core_data.tar.gz
docker compose exec database pg_dumpall -U taranis                  > "${backup_dir}/database_backup.sql"
