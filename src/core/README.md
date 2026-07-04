# Taranis AI Core

Core could be called the "backend" of Taranis AI.

It offers API Endpoints to the Frontend, is the sole persistence layer (via SQLAlchemy) and schedules tasks via RQ (Redis Queue).

## Requirements

* Python version 3.14 or greater.
* SQLite or PostgreSQL
* Redis


## Installation

Use the prebuilt container image from https://github.com/orgs/taranis-ai/packages/container/package/taranis-core


Or create a local setup for which it's recommended to use a uv to setup an virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
```

Source venv and install dependencies

```bash
source .venv/bin/activate
uv sync --all-extras --frozen --python 3.14 --no-install-package taranis-models
uv pip install -e ../models
```

This local-development setup intentionally uses the checked-out `../models` package.
Release/container builds still use the packaged `taranis-models` from the lockfile via `uv sync --frozen`.

## Usage

```bash
taranis-ai
```

## Frontend Cache Invalidation

Core owns frontend cache invalidation for write operations.

- `src/models/models/cache_contract.py` holds the shared cache defaults and key helpers used by both core and frontend
- `CACHE_ENABLED=true|false` toggles frontend-cache invalidation support in core
- `CACHE_REDIS_URL` optionally overrides the Redis URL used for frontend cache invalidation
- `CACHE_REDIS_PASSWORD` optionally overrides the Redis password used for frontend cache invalidation
- `RQ_DEFAULT_JOB_TIMEOUT` sets the default RQ job execution timeout in seconds for queues created by core
- when the cache-specific settings are unset, core falls back to `REDIS_URL` and `REDIS_PASSWORD`
- unit tests keep cache disabled by default through `build_config_overrides`
- admin configuration writes under `/api/config/*` currently invalidate the full frontend cache by design
- the manual invalidation endpoint is `POST /api/admin/cache/invalidate`
- `/api/assess/filter-lists` builds filter options from current database state on request; frontend caching may cache that response by user

## Health Endpoints

Core exposes two unauthenticated endpoints for monitoring:

* `/api/isalive` is a fast liveness probe for checking whether the API process responds.
* `/api/health` is the readiness and dependency health endpoint for database, broker, and workers where applicable.

`/api/health` returns `200` when all required services are healthy and `503` when a required dependency is down. In local or test environments using an in-memory broker, broker and worker checks are reported as `n/a`.

## API Error Responses

Core API handlers return JSON responses for structured payloads. Unexpected failures should be logged server-side and exposed to clients as generic error messages, not raw exception text or stack traces. Keep public validation messages only when clients need them to correct a submitted value.

## Development Setup

It is best to follow the [dev setup guide](../../dev/README.md)


### 0. Read the documentation

* [Flask](https://flask.palletsprojects.com)
* [SQLAlchemy](https://www.sqlalchemy.org/)

### 1. Setup Database
Set SQLAlchemy to use a temporary SQLite database.

```bash
export SQLALCHEMY_DATABASE_URI="sqlite:////tmp/taranis.db"
```

### 2. Start Flask

Run the Flask development server:

```bash
./install_and_run_dev.sh
```

This will start the Flask server and run the frontend service at `http://localhost:5000`.


### 3. Test

To run the unit tests just call:

```bash
uv run --no-sync --frozen python -m pytest tests/unit
```

Frontend-owned end-to-end tests now live in [../frontend/tests/playwright/README.md](../frontend/tests/playwright/README.md).
