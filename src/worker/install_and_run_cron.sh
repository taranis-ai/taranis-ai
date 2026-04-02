#!/bin/bash

set -eu

case "${DEBUG:-}" in
    ""|true|false|True|False|TRUE|FALSE|1|0|yes|no|on|off|YES|NO|ON|OFF)
        ;;
    *)
        export DEBUG=true
        ;;
esac

unset VIRTUAL_ENV

uv sync --all-extras --frozen --python 3.13 --no-install-package taranis-models
uv pip install --python .venv/bin/python -e ../models

uv run --no-sync --frozen python -m worker.cron_scheduler
