#!/bin/bash

# Check if watchman is installed (required for watch mode)
if ! command -v watchman &> /dev/null; then
    echo "Warning: watchman is not installed. Tailwind CSS watch mode may not work optimally."
    echo "Continuing anyway..."
    echo ""
fi

./build_tailwindcss.sh watch
