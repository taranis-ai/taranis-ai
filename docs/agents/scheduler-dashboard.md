# Scheduler Dashboard

## When To Load

Load this memory when working on the scheduler dashboard, scheduled jobs, active jobs, failed jobs, execution history, queue status, RQ registries, or routes below `/admin/scheduler`.

## Expected Behavior

- The admin scheduler dashboard shows queue and worker status plus tabs for scheduled jobs, active jobs, Queue Failures, Task Errors, and execution history.
- Each tab uses the standard Taranis table appearance and supports search, sorting, page size selection, and pagination.
- Only the selected tab is loaded during the initial page render. Other tabs load their first page when selected.
- Scheduled, active, failed, and persisted-error lists refresh every ten seconds only while their respective tabs are active. A refresh preserves each tab's current table query.
- Switching tabs clears table-specific query parameters and reloads the selected tab from its first page. Execution history loads when selected but does not poll.
- Direct links to a scheduler tab render the full dashboard with that tab selected. HTMX requests render only the requested table.
- Malformed or non-positive scheduler page and limit parameters fall back to the first page and default page size.
- The Admin Dashboard schedule count includes housekeeping jobs and matches the full Scheduled Jobs dataset.
- Datetimes are stored and returned as UTC values and displayed in the profile timezone through the frontend `format_datetime` filter.
- Failed-job error text is displayed through the scheduler error dialog and must be passed to the browser through Jinja JSON encoding.
- The Task Errors tab reads persisted task failures rather than the RQ failed registry. Current errors are latest failed outcomes per worker identity; All history contains every retained failure.
- The OSINT Source and Bot sidebar badges count failed configured workers and link to their respective lists filtered to failed states; one-off URL failures remain in Task Errors.
- Worker lists opened from an error badge show an active failure-filter banner. Its Show all link returns to the unfiltered worker list and works with or without HTMX.

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

- The first full dashboard render reads queue status, worker statistics, and only the selected tab's granular endpoint.
- Inactive tabs render lightweight HTMX placeholders and load from their granular endpoint when selected.
- Table query parameters are parsed by the frontend into `PagingData` and forwarded through `DataPersistenceLayer`.
- Core applies search, ordering, and pagination to RQ-backed lists before returning `items` and `total_count`; the frontend wraps that response in `CacheObject` for shared pagination controls.
- Scheduler list endpoints never return an unpaginated collection. The main dashboard counts unique configured cron jobs and RQ registry jobs, including housekeeping jobs, without fetching or annotating schedule rows.
- Execution-history statistics are returned as an aggregate mapping and are filtered, ordered, and paged in the frontend.
- Persisted errors are filtered, ordered, and paged in core through `/tasks/errors`. The `scope` is `current` or `history`, and the category is `all`, `collector`, or `bot`.
- A success or `NOT_MODIFIED` result resolves a Current error for the same worker identity without removing earlier failures from All history.
- Scheduler cache entries have short timeouts. Each distinct endpoint and paging query has its own list-cache key.

## Testing

- Frontend view coverage: `src/frontend/tests/unit/views/test_scheduler.py`
- Frontend end-to-end admin coverage: `src/frontend/tests/playwright/test_e2e_admin.py`
- Core queue manager coverage: `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`
- Core config API coverage: `src/core/tests/application/admin_console/configuration/test_config_api.py`
- Keep a configured-source consistency test asserting that the dedicated dashboard count matches the Scheduled Jobs aggregate total.
- Run focused tests from the relevant component directory while iterating, then run the component lint commands and `./dev/check_pyrefly.sh` after Python changes.

## Pitfalls

- Do not make frontend user-facing views import scheduler models from `models.admin`; scheduler routes are admin-only.
- Do not preload inactive scheduler tabs through the aggregate scheduler endpoint.
- Preserve the selected tab when table links update the browser URL.
- Do not carry `search`, `page`, `limit`, or `order` from one scheduler tab into another.
- Auto-refresh must not reset an active search, sort, page, or page-size selection.
- Runtime RQ registry data is not SQL-backed, so scheduler list filtering, ordering, and pagination are applied after collecting and annotating the registry entries.
- Do not use Queue Failures to explain sidebar badges: that tab is transient RQ state, while badge counts and Task Errors use retained database task rows.
- One-off `simple_web_collector` URL fetches are collector errors. They appear in Task Errors but not as synthetic rows in the configured OSINT Source table or its badge count.
- Core owns the `rq:cron:def` Redis hash. Startup reconciliation treats the current source, bot, and housekeeping specifications as an allowlist and removes every other persisted definition and its artifacts.
- Execution-history totals and per-worker statistics describe the full matching dataset, not only the visible page.
