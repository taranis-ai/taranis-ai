#!/bin/bash

# Copy Playwright E2E screenshots (docs_*.png) into the user documentation images.
# Example:
#   dev/sync_new_pictures.sh src/frontend/tests/playwright/screenshots docs/user/images

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <source_path> <destination_path>"
    exit 1
fi

# Assign arguments to variables
source_path=$1
destination_path=$2

# Check if source_path is a directory
if [ ! -d "$source_path" ]; then
    echo "Error: Source path is not a directory."
    exit 1
fi

# Check if destination_path is a directory
if [ ! -d "$destination_path" ]; then
    echo "Error: Destination path is not a directory."
    exit 1
fi

# Pictures to skip
skip_files=("docs_osint_sources.png" "docs_dashboard.png" "docs_osint_sources_add.png")

# Pictures to copy to <destination>/osint
osint_files=("docs_bot_selection.png" "docs_source_groups.png" "docs_wordlist_usage.png" "docs_wordlists.png")

# Function to check if an element is in an array
contains() {
    local e
    for e in "${@:2}"; do [[ "$e" == "$1" ]] && return 0; done
    return 1
}

# Create osint subfolder if it doesn't exist
osint_folder="$destination_path/osint"
mkdir -p "$osint_folder"

# Copy files with the prefix "docs_" from source_path to destination_path
for file in "$source_path"/docs_*;
do
    filename=$(basename "$file")
    if [ -e "$file" ]; then
        if ! contains "$filename" "${skip_files[@]}"; then
            new_filename="${filename#docs_}"  # Remove the prefix "docs_"
            if contains "$filename" "${osint_files[@]}"; then
                cp "$file" "$osint_folder/$new_filename"
                echo "Copied $filename to osint/$new_filename"
            else
                cp "$file" "$destination_path/$new_filename"
                echo "Copied $filename to $new_filename"
            fi
        else
            echo "Skipping $filename"
        fi
    fi
done
echo "Files with prefix 'docs_' have been copied and renamed from $source_path to $destination_path."
