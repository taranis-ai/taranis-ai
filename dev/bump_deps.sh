#!/bin/bash

cd $(git rev-parse --show-toplevel)

pre-commit autoupdate

uv sync --upgrade --all-extras --directory src/core
uv sync --upgrade --all-extras --directory src/worker
uv sync --upgrade --all-extras --directory src/models
uv sync --upgrade --all-extras --directory src/frontend

pushd src/frontend
deno outdated --update

