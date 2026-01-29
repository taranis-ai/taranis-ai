#!/usr/bin/env bash
# Wrapper script for docker compose to avoid dev environment variable conflicts
# Usage: ./compose.sh up -d
#        ./compose.sh ps
#        ./compose.sh logs -f

# Unset dev environment variables that shouldn't affect docker compose
unset TARANIS_CORE_URL

# Run docker compose with all provided arguments
exec docker compose "$@"
