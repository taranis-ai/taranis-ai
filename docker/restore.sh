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
    local volume_name="${compose_project_name}_${2}"
    echo "Restoring PostgreSQL database from $backup_file..."
    docker run --rm -d \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-taranis}" \
        -v ./$backup_dir:/tmp \
        -v ./db_init.sh:/docker-entrypoint-initdb.d/db_init.sh \
        -v $volume_name:/var/lib/postgresql/data \
        --name "${compose_project_name}_database_restore" docker.io/library/postgres:14
}

# Function to restore data to a Docker volume
restore_volume_data() {
    local backup_file="$1"
    echo $backup_file
    local volume_name="${compose_project_name}_${2}"

    echo "Restoring data to $volume_name from $backup_file..."
    docker run --rm -d --name "${compose_project_name}_core_restore" \
    -v "$volume_name:/app/data" -v ./backups:/backups:z busybox \
    tar -xzvf "$backup_file" -C /app/data
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
if [ ! -f "$database_backup_file" ] ; then
    echo "Error: Backup file $database_backup_file was not found in the specified directory."
    exit 1
elif [ ! -f "$core_data_backup_file" ] ; then
    echo "Error: Backup file $core_data_backup_file was not found in the specified directory."
    exit 1
fi

# Check if the necessary volumes are empty
echo "Checking if the necessary volumes are empty..."
check_volume_exists "core_data"
check_volume_exists "database_data"

# Perform the actual restore operations
restore_volume_data "$core_data_backup_file" "core_data"
restore_postgresql "$database_backup_file" "database_data"

echo "Restore completed successfully."
