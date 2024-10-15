#!/bin/bash
set -euox pipefail
source ./backup.sh
docker compose down core gui && \
docker compose down database --volumes && \
source ./restore.sh --database $backup_dir && \
docker compose up -d

