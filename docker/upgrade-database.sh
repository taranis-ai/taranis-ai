#!/bin/bash
set -euo pipefail
source ./backup.sh --upgrade
docker compose down core gui && \
docker compose down database --volumes && \
source ./restore.sh --database $backup_dir && \
docker compose up -d

