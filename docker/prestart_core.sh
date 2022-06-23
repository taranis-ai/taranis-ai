#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running migrations..."
flask db migrate
echo "Done."
