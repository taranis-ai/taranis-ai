# Architecture and Boundaries

## When To Load

Before component, API, workflow, background-job, persistence, migration, or datetime changes.

## Components and Tasks

- `src/core/`: Flask REST API and SQLAlchemy persistence.
- `src/frontend/`: Flask, HTMX, Alpine, DaisyUI, and Tailwind.
- `src/worker/`: RQ collectors, bots, presenters, publishers, connectors, and miscellaneous tasks.
- `src/models/`: shared Pydantic input/output contracts.
- `src/ingress/`: Nginx routing.

`src/core/core/managers/queue_manager.py` owns Redis-backed RQ scheduling and cron expressions.

## API Boundaries

- User-facing frontend views must not import `models.admin` or use admin/config endpoints. Publishing reference data belongs in user-scoped `src/core/core/api/publish.py` endpoints and `src/models/models/product.py` models.
- Prefer frontend `DataPersistenceLayer`; direct `CoreApi()` calls are for raw responses, downloads/streams, or deliberate cache bypasses.
- Config/admin blueprints share constraint handling in `src/core/core/api/config.py`: rollback, then safe unique/not-null validation messages (400) or a logged static 500 for other integrity errors. Pydantic errors use the shared formatter and rollback boundary. Endpoint catch-alls must let `IntegrityError` and `ValidationError` reach it; curated bot-index conflicts retain their domain message. Coverage: `src/core/tests/unit/test_config_integrity_errors.py`.

## Persistence and Datetimes

- New tables are created from metadata by `src/core/core/managers/db_manager.py`; do not add migrations for them.
- For existing-table changes/deletion, compare with `master`; do not migrate temporary unmerged changes.
- Launch core once to bootstrap the current database before a migration. If the latest migration is only marked applied, undo/unmark it before reapplying.
- Core's naive persisted datetimes represent UTC. Store UTC clock values, preserve that interpretation during serialization, and normalize incoming Assess/story/news timestamps through `src/models/models/assess.py`. Never persist local `datetime.now()` values in naive columns.
