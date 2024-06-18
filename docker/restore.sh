#!/bin/bash

set -euo pipefail

# Function to display script usage
usage() {
    echo "Usage: $0 <backup_dir>"
    exit 1
}

# Function to check if a volume is empty using a temporary container
check_volume_empty() {
    local volume_name=$1
    local temp_container="temp_${volume_name}_checker"

    # Check if volume is empty by trying to list files in it
    if docker run --rm --name "$temp_container" -v "$volume_name:/volume" busybox find /volume -mindepth 1 -print -quit | grep -q .; then
        echo "Error: Volume $volume_name is not empty. Restore aborted."
        exit 1
    fi
}

# Function to restore PostgreSQL database from a backup file
restore_postgresql() {
    local backup_file="$1"
    echo "Restoring PostgreSQL database from $backup_file..."
    docker compose exec -T database psql -U postgres -v ON_ERROR_STOP=1 < "$backup_file"
}

# Function to restore data to a Docker volume
restore_volume_data() {
    local backup_file="$1"
    local volume_name="$2"
    echo "Restoring data to $volume_name from $backup_file..."
    docker compose run --rm -v "$volume_name:/data" busybox tar xzvf "$backup_file" -C /data
}

# Main script execution starts here

# Check for required argument
if [ $# -ne 1 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

backup_dir=$1
database_backup_file="$backup_dir/database_backup.sql"
core_data_backup_file="$backup_dir/core_data.tar.gz"

# Validate backup files exist
if [ ! -f "$database_backup_file" ] || [ ! -f "$core_data_backup_file" ]; then
    echo "Error: Backup files not found in the specified directory."
    exit 1
fi

# Check if the necessary volumes are empty
echo "Checking if the necessary volumes are empty..."
check_volume_empty "core_data"
check_volume_empty "database_data"

# Perform the actual restore operations
restore_postgresql "$database_backup_file"
restore_volume_data "$core_data_backup_file" "core_data"

echo "Restore completed successfully."
