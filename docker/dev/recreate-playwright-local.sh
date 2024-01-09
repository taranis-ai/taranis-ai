#!/bin/bash

cd $(git rev-parse --show-toplevel)
cd docker/dev

docker compose down --volumes database

docker compose -f compose.yml up -d database 

docker cp ../../resources/e2e_test_db.sql dev-database-1:/tmp

sleep 3

docker exec -i --workdir /usr/local/bin dev-database-1 bash -c "psql -U taranis taranis < /tmp/e2e_test_db.sql"
