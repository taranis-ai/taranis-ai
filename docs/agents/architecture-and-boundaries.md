# Architecture and Boundaries

Read before component, API, workflow, background-job, persistence, migration, or datetime changes.

## Components and Tasks

- `src/core/`: Flask REST API and SQLAlchemy persistence.
- `src/frontend/`: Flask, HTMX, Alpine, DaisyUI, and Tailwind.
- `src/worker/`: RQ collectors, bots, presenters, publishers, connectors, and miscellaneous tasks.
- `src/models/`: shared Pydantic input/output contracts.
- `src/ingress/`: Nginx routing.

`src/core/core/managers/queue_manager.py` owns Redis-backed RQ scheduling and cron expressions.

## Shared Validation

- Put intrinsic input types, defaults, required fields, constraints, normalization, and payload-only cross-field rules in `src/models/` Pydantic contracts. Prefer built-in types and `Field` constraints before custom validators; reuse those models at API/worker input boundaries.
- Keep permissions, database references/uniqueness, transactions, and runtime checks in services and persistence. Shared validators must not perform database/network I/O or import application code.
- Distinguish creation, partial-update, and response requirements when needed; do not tighten a response model to enforce creation rules.
- [Worker Parameters](worker-parameters.md) is the existing example of model-owned rules and schema-derived forms. Reuse supported schema constraints for frontend feedback; server-side validation remains authoritative for custom validators.

## API Boundaries

- User-facing frontend views must not import `models.admin` or use admin/config endpoints. Publishing reference data belongs in user-scoped `src/core/core/api/publish.py` endpoints and `src/models/models/product.py` models.
- Prefer frontend `DataPersistenceLayer`; direct `CoreApi()` calls are for raw responses, downloads/streams, or deliberate cache bypasses.
- Config/admin blueprints share constraint handling in `src/core/core/api/config.py`: rollback, then safe unique/not-null validation messages (400) or a logged static 500 for other integrity errors. PostgreSQL duplicate messages identify fields only when the constraint matches a known unique model column; unknown constraints use a generic duplicate message. SQLite uses structured constraint codes for duplicate/required-value messages, never parsed SQL or driver text. Pydantic errors use the shared formatter and rollback boundary. Endpoint catch-alls must let `IntegrityError` and `ValidationError` reach it; curated bot-index conflicts retain their domain message. Coverage: `src/core/tests/unit/test_config_integrity_errors.py` and admin configuration API tests.

## Persistence and Datetimes

- SQLAlchemy 2.1 session execution requires executable statements: wrap standalone EXISTS in SELECT and never pass a legacy ORM Query to `execute`. Use explicit `.subquery()` when placing a `Select` in a FROM clause. `BaseModel.get_filtered_count` removes sorting/pagination before wrapping the filtered query, retaining grouping and HAVING. Model query coverage is in `src/core/tests/unit/test_model_queries.py`.
- Use plain `.distinct()` to deduplicate complete model rows across SQLite/PostgreSQL; `.distinct(column)` is the deprecated PostgreSQL-only DISTINCT ON API. `OSINTSource.get_all_for_collector` joins a unique task primary key and needs no DISTINCT.
- SQLAlchemy 2.1 types result columns individually. Use directly imported `sqlalchemy.select` for typed multi-column queries and row mappings for named aggregate columns; `.tuples()` is deprecated.
- New tables are created from metadata by `src/core/core/managers/db_manager.py`; do not add migrations for them.
- For existing-table changes/deletion, compare with `master`; do not migrate temporary unmerged changes.
- Launch core once to bootstrap the current database before a migration. If the latest migration is only marked applied, undo/unmark it before reapplying.
- Core's naive persisted datetimes represent UTC. Store UTC clock values, preserve that interpretation during serialization, and normalize incoming Assess/story/news timestamps through `src/models/models/assess.py`. Never persist local `datetime.now()` values in naive columns.
