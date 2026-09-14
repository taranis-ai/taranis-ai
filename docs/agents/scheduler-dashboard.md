# Scheduler Dashboard

## When To Load

`/admin/scheduler`, RQ registries, scheduled/active/failed jobs, execution history, or source/bot failure badges.

## Contracts

- Initial render loads queue/worker status and only the selected tab. Other tabs load on selection; direct links render the full dashboard, HTMX requests only the table.
- Auto-refresh defaults off. Enabled refresh runs every 10 seconds for queue cards and the active scheduled/active/failed tab, preserving its query. History does not poll.
- Switching tabs resets search/page/limit/order; table navigation retains the selected tab. Malformed/non-positive page/limit falls back to defaults.
- Core filters/orders/pages RQ lists after collecting registry entries; they are not SQL-backed. Endpoints always return paginated `items`/`total_count`, cached separately per endpoint/query.
- Schedule counts include unique configured cron jobs, registry jobs, and housekeeping without fetching/annotating full rows. Admin Dashboard count must match the full Scheduled Jobs dataset.
- History statistics arrive as an aggregate mapping, filtered/ordered/paged in frontend; totals/statistics describe the full matching dataset.
- History and dashboard task totals count `WARNING` separately from successes and failures. Warnings contribute to total outcomes but not the full-success percentage; a warning-only/mixed-success group shows a yellow warning badge instead of All Success. Warnings still update last-success tracking because collection completed without failing.
- Source/Bot badges use latest persisted results for configured workers, not transient Queue Failures. Select latest statuses in SQL before counting/paging; exclude one-off `simple_web_collector` fetches. Failure filters preserve other query settings and reset pagination.
- Display UTC values in profile timezone via `format_datetime`. Pass curated failure messages to the browser with Jinja JSON encoding.
- Core owns `rq:cron:def`: startup treats current source/bot/housekeeping specs as an allowlist and removes other persisted definitions and artifacts.

## Entry Points and Coverage

`src/frontend/frontend/views/admin_views/scheduler_views.py`, `src/frontend/frontend/templates/schedule/`, `src/core/core/managers/queue_manager.py`, `src/core/core/api/config.py`, `src/core/core/service/dashboard.py`, `src/core/core/service/task.py`; contracts in `src/models/models/admin.py` and `src/models/models/task.py`.

Tests: `src/frontend/tests/unit/views/test_scheduler.py`, `src/frontend/tests/playwright/test_e2e_admin.py`, `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`, `src/core/tests/application/admin_console/configuration/test_config_api.py`. Retain dashboard-count versus Scheduled Jobs aggregate consistency coverage.
