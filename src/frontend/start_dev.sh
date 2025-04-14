#!/bin/bash

set -eu

if [ ! -f ".env" ]; then
    cp env.sample .env
fi

./extend_tmux.sh