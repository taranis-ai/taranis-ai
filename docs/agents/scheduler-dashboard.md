# Scheduler Dashboard

## When To Load

Scheduler dashboard, scheduled jobs, active jobs, failed jobs, execution history, queue status, RQ registries, or routes below `/admin/scheduler`.

## Expected Behavior

- The admin scheduler dashboard shows queue and worker status plus tabs for scheduled, active, failed, and historical jobs.
- Each tab uses the standard Taranis table appearance and supports search, sorting, page size selection, and pagination.
- Scheduled, active, and failed job lists refresh only while their respective tabs are active. A refresh preserves each tab's current table query.
- Switching tabs clears table-specific query parameters and loads the selected tab from its first page. Execution history refreshes once when selected but does not poll.
- Direct links to a scheduler tab render the full dashboard with that tab selected. HTMX requests render only the requested table.
- Malformed or non-positive scheduler page and limit parameters fall back to the first page and default page size.
- Datetimes are stored and returned as UTC values and displayed in the profile timezone through the frontend `format_datetime` filter.
- Failed-job error text is displayed through the scheduler error dialog and must be passed to the browser through Jinja JSON encoding.

## Code Paths

- Frontend routes: `src/frontend/frontend/router/admin.py`
- Frontend views: `src/frontend/frontend/views/admin_views/scheduler_views.py`
- Dashboard and table templates: `src/frontend/frontend/templates/schedule/`
- Shared table macros: `src/frontend/frontend/templates/macros/table.html`
- Scheduler response models: `src/models/models/admin.py`
- Task history models: `src/models/models/task.py`
- Core scheduler endpoints: `src/core/core/api/config.py`
- Core queue and registry data: `src/core/core/managers/queue_manager.py`
- Admin dashboard schedule count: `src/core/core/service/dashboard.py`
- Task history endpoint and service: `src/core/core/api/task.py`, `src/core/core/service/task.py`

## Data Flow

- The first full dashboard render reads the aggregate scheduler dashboard endpoint and task history endpoint.
- Subsequent HTMX refreshes use the granular scheduled, active, failed, queue, and task-history endpoints.
- Table query parameters are parsed by the frontend into `PagingData` and forwarded through `DataPersistenceLayer`.
- Core applies search, ordering, and pagination to RQ-backed lists before returning `items` and `total_count`; the frontend wraps that response in `CacheObject` for shared pagination controls.
- Execution-history statistics are returned as an aggregate mapping and are filtered, ordered, and paged in the frontend.
- Scheduler cache entries have short timeouts. Each distinct endpoint and paging query has its own list-cache key.

## Testing

- Frontend view coverage: `src/frontend/tests/unit/views/test_scheduler.py`
- Frontend end-to-end admin coverage: `src/frontend/tests/playwright/test_e2e_admin.py`
- Core queue manager coverage: `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`
- Core config API coverage: `src/core/tests/application/admin_console/configuration/test_config_api.py`
- Run focused tests from the relevant component directory while iterating, then run the component lint commands and `./dev/check_pyrefly.sh` after Python changes.

## Pitfalls

- Do not make frontend user-facing views import scheduler models from `models.admin`; scheduler routes are admin-only.
- Keep the initial aggregate fetch to avoid multiplying core calls during full-page rendering.
- Preserve the selected tab when table links update the browser URL.
- Do not carry `search`, `page`, `limit`, or `order` from one scheduler tab into another.
- Auto-refresh must not reset an active search, sort, page, or page-size selection.
- Runtime RQ registry data is not SQL-backed, so scheduler list filtering, ordering, and pagination are applied after collecting and annotating the registry entries.
- Execution-history totals and per-worker statistics describe the full matching dataset, not only the visible page.
