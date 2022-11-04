#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running migrations..."
/app/db_migration.py db upgrade head

if [ `./manage.py collector --list | wc -l` = 0 -a x"$SKIP_DEFAULT_COLLECTOR" != "xtrue" ]; then
    (
    echo "Adding default collector"
    ./manage.py collector --create --name "Default Docker Collector" --description "A local collector node configured as a part of Taranis NG default installation." --api-url "http://collectors/" --api-key "$COLLECTOR_PRESENTER_PUBLISHER_API_KEY"
    ) &
fi

echo "Done."
