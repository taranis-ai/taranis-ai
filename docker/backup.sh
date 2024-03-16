#!/bin/bash

backup_dir="/backups/$(date -Im)"

mkdir -p "${backup_dir}"

docker compose run --rm -v "$(pwd)"/backups:/backups core tar czvf "${backup_dir}"/core_data.tar.gz /data
docker compose exec database pg_dumpall -U postgres > "${backup_dir}"/database_backup.sql
