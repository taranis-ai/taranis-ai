#!/bin/bash

set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script is only supported on macOS."
    exit 1
fi

if [ "${EUID}" -ne 0 ]; then
    echo "Run this script with sudo:"
    echo "  sudo ./dev/manage_macos_nginx.sh"
    exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required to manage the macOS nginx setup."
    exit 1
fi

BREW_PREFIX=$(brew --prefix)
NGINX_BIN="$BREW_PREFIX/opt/nginx/bin/nginx"
PID_FILE="$BREW_PREFIX/var/run/nginx.pid"

if [ ! -x "$NGINX_BIN" ]; then
    echo "Homebrew nginx is not installed at $NGINX_BIN."
    echo "Install it with: brew install nginx"
    exit 1
fi

nginx_running() {
    local pid

    [ -s "$PID_FILE" ] || return 1

    pid=$(tr -d '[:space:]' < "$PID_FILE")
    [ -n "$pid" ] || return 1

    case "$pid" in
        *[!0-9]*)
            return 1
            ;;
    esac

    kill -0 "$pid" 2>/dev/null || return 1

    ps -p "$pid" -o command= 2>/dev/null | grep -F "$NGINX_BIN" >/dev/null 2>&1
}

"$NGINX_BIN" -t

if nginx_running; then
    "$NGINX_BIN" -s reload
else
    "$NGINX_BIN"
fi
