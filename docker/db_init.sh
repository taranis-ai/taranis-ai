#!/bin/bash
set -e

pg_restore --verbose --clean --if-exists --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" /tmp/database_backup.tar

psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" -c "ALTER DATABASE $POSTGRES_DB REFRESH COLLATION VERSION;"

pg_ctl -D "$PGDATA" -m fast stop
