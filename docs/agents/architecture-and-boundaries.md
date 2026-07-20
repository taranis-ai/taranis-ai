# Architecture and Boundaries

## When To Load

Before changing application components, API boundaries, user-facing workflows, background jobs, persistence, migrations, or datetime handling.

## Components

- `src/core/`: Flask REST API using SQLAlchemy ORM
- `src/ingress/`: Nginx routing to frontend and backend
- `src/frontend/`: Flask, HTMX, DaisyUI, and Tailwind CSS
- `src/worker/`: RQ workers for collectors, bots, presenters, and publishers
- `src/models/`: Pydantic input/output models

## Background Tasks

RQ uses Redis on port 6379 for queueing and persistence. `src/core/core/managers/queue_manager.py` schedules and enqueues jobs with RQ's scheduler and cron expressions via `croniter>=6.0.0`.

Worker task modules are `collector_tasks.py`, `bot_tasks.py`, `presenter_tasks.py`, `publisher_tasks.py`, `connector_tasks.py`, and `misc_tasks.py`.

## Frontend and API Boundaries

- User-facing frontend views must not import `models.admin`.
- Do not use admin/config endpoints in `src/core/core/api/config.py` from user-facing views.
- Expose user workflow product or publishing reference data through a user-scoped endpoint in `src/core/core/api/publish.py`, with matching models in `src/models/models/product.py`.
- Prefer `DataPersistenceLayer` in frontend views. Use `CoreApi()` directly only for raw responses, downloads/streams, or deliberate cache bypasses.

## Persistence and Migrations

- Do not create migrations for new tables: core creates them from metadata in `src/core/core/managers/db_manager.py` after `db.init_app(app)` and metadata setup.
- For existing-table changes or deletion, compare with `master` before adding a migration. Do not migrate a temporary, unmerged branch-only change.
- Before a core migration, launch core once to bootstrap the current database. If the latest migration is only marked applied, undo or unmark it before reapplying.

## Datetimes

- Persisted naive datetimes in core represent UTC.
- Normalize incoming assess/story/news timestamps through `src/models/models/assess.py` where applicable.
- Store UTC clock values in naive SQLAlchemy `DateTime` columns. Do not persist local `datetime.now()` values.
- Preserve the UTC convention when serializing naive core datetimes.
- Do not leave trailing whitespace.
