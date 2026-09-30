#!/bin/bash
set -e

pg_restore --verbose --clean --if-exists --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" /tmp/database_backup.tar

psql --set=ON_ERROR_STOP=1 --set=dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" <<'SQL'
ALTER DATABASE :"dbname" REFRESH COLLATION VERSION;
SQL
