#!/bin/bash

export GRANIAN_WORKERS=$((${WORKERS_PER_CORE:-2} * $(nproc)))
LOG_LEVEL=${LOG_LEVEL:-info}

if [[ "${DEBUG,,}" == "true" ]]; then
    LOG_LEVEL="debug"
fi

export GRANIAN_LOG_LEVEL=$LOG_LEVEL

# Start Granian
exec granian run
