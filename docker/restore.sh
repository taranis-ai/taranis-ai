#!/bin/bash
set -euo pipefail

# Function to display script usage
usage() {
    echo "Usage: $0 [--core | --database] <backup_dir>"
    echo
    echo "If no options are provided, both core and database components will be executed."
    echo "Options (choose only one):"
    echo "  --core       Execute only the core component."
    echo "  --database   Execute only the database component."
    exit 1
}

# Function to check if a volume exists
check_volume_exists() {
    local volume_name=$1
    echo "Checking if the volume exists: ${compose_project_name}_$volume_name"

    if docker volume ls | grep -q "${compose_project_name}_$volume_name"; then
        echo "Error: Volume ${volume_name} already exists. Ensure you have a backup of your data and delete the volume before continuing your restore."
        exit 1
    fi
}

# Function to restore PostgreSQL database from a backup file
restore_postgresql() {
    local backup_file="$1"
    local volume_name="${compose_project_name}_${2}"
    echo "Restoring PostgreSQL database from $backup_file..."
    docker run --rm \
        -e POSTGRES_DB="${DB_DATABASE:-taranis}" \
        -e POSTGRES_USER="${DB_USER:-taranis}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-taranis}" \
        -v $backup_file:/tmp/database_backup.tar \
        -v ./db_init.sh:/docker-entrypoint-initdb.d/db_init.sh:z \
        -v $volume_name:/var/lib/postgresql/data \
        --name "${compose_project_name}_database_restore" docker.io/library/postgres:17-alpine

    if [ $? -ne 0 ]; then echo "Database restoration failed"; exit 1; fi
}

# Function to restore core data to a Docker volume
restore_volume_data() {
    local backup_file="$1"
    local volume_name="${compose_project_name}_${2}"

    echo "Restoring data to $volume_name from $backup_file..."
    docker run --rm -d --name "${compose_project_name}_core_restore" \
    -v "$volume_name:/app/data" -v ./backups:/backups:z busybox \
    tar -xzvf "$backup_file" -C /app/data

    if [ $? -ne 0 ]; then echo "Core volume restoration failed"; exit 1; fi
}

run_core=false
run_database=false
component_flags=0

# Parse options
options=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --core)
            run_core=true
            component_flags=$(( component_flags + 1 ))
            shift
            ;;
        --database)
            run_database=true
            component_flags=$(( component_flags + 1 ))
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Error: Unknown option '$1'"
            usage
            ;;
        *)
            # Assume the backup_dir
            options+=("$1")
            shift
            ;;
    esac
done

# If more than one component flag is provided, return a warning and exit
if [ "$component_flags" -gt 1 ]; then
    echo "Warning: You have provided multiple component flags (--core and --database)."
    echo "Please remove the flags to execute both components, or specify only one component."
    exit 1
fi

# If no component flags are provided, execute both components
if [ "$component_flags" -eq 0 ]; then
    run_core=true
    run_database=true
fi

# Validate backup_dir argument
if [ ${#options[@]} -ne 1 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

backup_dir="${options[0]}"
backup_dir="${backup_dir%/}"

[[ -f .env ]] && source .env

# Set backup file paths
database_backup_file="$backup_dir/database_backup.tar"
core_data_backup_file="$backup_dir/core_data.tar.gz"
compose_project_name="${COMPOSE_PROJECT_NAME:-$(basename "$(pwd)")}"

# Validate that backup_dir is a directory
if [ -f "$backup_dir" ]; then
    echo "Error: '$backup_dir' is a file; please choose a directory containing backup files."
    exit 1
fi

if $run_database && [ ! -f "$database_backup_file" ]; then
    echo "Error: Backup file '$database_backup_file' was not found in the specified directory: '$backup_dir'."
    exit 1
fi

if $run_core && [ ! -f "$core_data_backup_file" ]; then
    echo "Error: Backup file '$core_data_backup_file' was not found in the specified directory: '$backup_dir'."
    exit 1
fi

if $run_core; then
    check_volume_exists "core_data"
fi

if $run_database; then
    check_volume_exists "database_data"
fi

# Restore operations
docker compose up --no-start core database

if $run_core; then
    restore_volume_data "$core_data_backup_file" "core_data"
fi

if $run_database; then
    restore_postgresql "$database_backup_file" "database_data"
fi

echo "Restore completed successfully."
