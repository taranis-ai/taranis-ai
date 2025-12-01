#!/bin/bash

cd $(git rev-parse --show-toplevel)

uv sync --upgrade --all-extras --directory src/core
uv sync --upgrade --all-extras --directory src/worker
uv sync --upgrade --all-extras --directory src/models
uv sync --upgrade --all-extras --directory src/frontend

