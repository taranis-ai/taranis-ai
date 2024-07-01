#!/bin/bash

set -euo pipefail

# Function to display script usage
usage() {
    echo "Usage: $0 <backup_dir>"
    exit 1
}



# Function to check if a volume is empty using a temporary container
check_volume_exists() {
    local volume_name=$1
    if docker volume ls | grep  $volume_name; then 
    exit "Volume ${volume_name} already exists, ensure you have a backup of your data and delete the volume before continuing your restore"
    fi
}

# Function to restore PostgreSQL database from a backup file
restore_postgresql() {
    local backup_file="$1"
    echo "Restoring PostgreSQL database from $backup_file..."
    docker run --rm -d \
        -e POSTGRES_DB="${DB_DATABASE:-taranis}" \
        -e POSTGRES_USER="${DB_USER:-taranis}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-taranis}" \
        -v ./$backup_dir:/docker-entrypoint-initdb.d \
        -v $database_volume_name:/var/lib/postgresql/data \
        --name taranis_database_restore docker.io/library/postgres:14
}

# Function to restore data to a Docker volume
restore_volume_data() {
    local backup_file="$1"

    echo "Restoring data to $core_volume_name from $backup_file..."
    docker run --rm -d --name taranis_core_restore \
    -v "$core_volume_name:/app/data" -v ./backups:/backups:z busybox \
    tar xzvf '$backup_file' -C /app/data
}

get_compose_volume_name() {
    COMPOSE_FILE="compose.yml"
    if [ ! -f "$COMPOSE_FILE" ]; then
    echo "$COMPOSE_FILE not found!"
    exit 1
    fi

    database_volume_name=""
    core_volume_name=""

    volume_lines=$(awk '/volumes:/ {flag=1; next} flag' $COMPOSE_FILE)

    while read -r line; do
    volume_name=$(echo "$line" | awk '{print $1}')
    
    # Prepend project name
    prefixed_volume_name="${COMPOSE_PROJECT_NAME}_${volume_name%:}"

    # Check for substrings and assign to correct variable
    if [[ "$volume_name" == *database* ]]; then
        database_volume_name="$prefixed_volume_name"
    elif [[ "$volume_name" == *core* ]]; then
        core_volume_name="$prefixed_volume_name"
    fi
    done <<< "$volume_lines"
    }

# Main script execution starts here

# Check for required argument
if [ $# -ne 1 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

[[ -f .env ]] && source .env


backup_dir=$1
backup_dir="${backup_dir%/}"
database_backup_file="$backup_dir/database_backup.sql"
core_data_backup_file="$backup_dir/core_data.tar.gz"
compose_project_name=${COMPOSE_PROJECT_NAME:-$(basename $(pwd))}


# Validate backup files exist
if [ ! -f "$database_backup_file" ] || [ ! -f "$core_data_backup_file" ]; then
    echo "Error: Backup files not found in the specified directory."   ## TODO be more verbose about the issue
    exit 1
fi

# Check if the necessary volumes are empty
echo "Checking if the necessary volumes are empty..."
check_volume_exists "core_data"
check_volume_exists "database_data"

get_compose_volume_name
echo $core_volume_name
echo $database_volume_name
# Perform the actual restore operations
restore_postgresql "$database_backup_file"
restore_volume_data "$core_data_backup_file"

docker rm -f taranis_database_restore

echo "Restore completed successfully."
