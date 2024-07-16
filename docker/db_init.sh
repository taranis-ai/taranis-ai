#!/bin/bash
set -e

pg_restore --verbose --clean --if-exists --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" /tmp/database_backup.tar && \
exit $?
