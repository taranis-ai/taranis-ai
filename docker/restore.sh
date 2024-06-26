#!/bin/bash

set -euo pipefail

# Function to display script usage
usage() {
    echo "Usage: $0 <backup_dir>"
    exit 1
}

# Function to check if a volume is empty using a temporary container
check_volume_empty() {   ## TODO rename check_volume_exists
    local volume_name=$1
    docker volume ls | grep -q $database_volume_name && exit "Database volume exists"  ## TODO: more verbose like below
    docker volume ls | grep -q $core_volume_name     && exit "Core data volume ${core_volume_name} already exists, ensure you have a backup of your data and delete the volume before contiouing your restore"
}

# Function to restore PostgreSQL database from a backup file
restore_postgresql() {
    local backup_file="$1"
    echo "Restoring PostgreSQL database from $backup_file..."
	 volume_name=TODO_IMPLEMENT
	 backup_dir=TODO_IMPLEMENT
    # dropdb taranis -U taranis --force
    # createuser --superuser -U taranis tmp
    # createdb --owner taranis -U taranis taranis
	 docker run --rm \
		 -e TARAINS_DB="${DB_DATABASE:-taranis}" \
		 -e TARANIS_USER="${DB_USER:-taranis}" \
		 -e TARANIS_PASSWORD="${POSTGRES_PASSWORD:-taranis}" \
		 -v $volume_name:/var/lib/postgresql/data \
		 -v $backup_dir:/docker-entrypoint-initdb.d \
		 --name taranis_database_restore docker.io/library/postgres:14
}

# Function to restore data to a Docker volume
restore_volume_data() {
    local backup_file="$1"
    local volume_name="$2"
    echo "Restoring data to $volume_name from $backup_file..."
    docker run --rm -v "$volume_name:/data" -v ./backups:/backups:Z busybox tar xzvf "$backup_file" -C /data
}

# Main script execution starts here

# Check for required argument
if [ $# -ne 1 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

[[ -f .env ]] && source .env

backup_dir=$1
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
check_volume_empty "core_data"
check_volume_empty "database_data"

# Perform the actual restore operations
restore_postgresql "$database_backup_file"
restore_volume_data "$core_data_backup_file" "core_data"

echo "Restore completed successfully."
