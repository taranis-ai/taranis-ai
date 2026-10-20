# Scheduler Dashboard

## When To Load

`/admin/scheduler`, RQ registries, scheduled/active/failed jobs, execution history, or source/bot failure badges.

## Contracts

- Initial render loads queue/worker status and only the selected tab. Other tabs load on selection; direct links render the full dashboard, HTMX requests only the table.
- Auto-refresh defaults off. Enabled refresh runs every 10 seconds for queue cards and the active scheduled/active/failed tab, preserving its query. History does not poll.
- Switching tabs resets search/page/limit/order; table navigation retains the selected tab. Malformed/non-positive page/limit falls back to defaults.
- Core filters/orders/pages RQ lists after collecting registry entries; they are not SQL-backed. Endpoints always return paginated `items`/`total_count`, cached separately per endpoint/query.
- Schedule counts include unique configured cron jobs, registry jobs, and housekeeping without fetching/annotating full rows. Admin Dashboard count must match the full Scheduled Jobs dataset.
- Completed Runs lists persisted terminal results across users and background jobs, including committed pipeline steps, newest first. `/api/tasks/runs` uses the existing scheduler read permission, validates outcome/search/sort/paging, caps page size at 100 while returning the full matching count, omits private result data, and replaces historical failure text with curated reason messages. The frontend `/admin/scheduler/completed` supports direct links, HTMX, outcome filtering, pagination, and opt-in refresh while preserving its query. It is independent of Redis result expiry.
- Worker Summary (the existing history tab) statistics arrive as an aggregate mapping, filtered/ordered/paged in frontend; totals/statistics describe the full matching dataset.
- History and dashboard task totals count `WARNING` separately from successes and failures. Warnings contribute to total outcomes but not the full-success percentage; a warning-only/mixed-success group shows a yellow warning badge instead of All Success. Warnings still update last-success tracking because collection completed without failing.
- Source/Bot badges use latest persisted results for configured workers, not transient Queue Failures. Select latest statuses in SQL before counting/paging; exclude one-off `simple_web_collector` fetches. Failure filters preserve other query settings and reset pagination.
- Associate status by `Task.worker_id` and task family, never job-ID patterns. Source failure queries rank results per worker by last-run, last-success, then job-ID descending. Task writers must populate worker identity; scheduled-job history still uses job IDs.
- Sidebar views share one badge response per request, even without frontend caching. Missing/error results give zero badges; authorization failures propagate.
- Display UTC values in profile timezone via `format_datetime`. Queue Failures shows the safe failure summary in the row and full diagnostics through View Error: known reason, actual enqueued execution budget, attempts, checkpointed bot/stage progress, continuation exhaustion, and job ID for worker-log correlation. Legacy jobs explicitly show that no checkpoint was recorded. Pass diagnostics with Jinja JSON encoding and render with `textContent`.
- `QUEUE_ENABLED=false` explicitly skips Redis initialization and startup scheduling. Enabled queues check Redis readiness up to five times, waiting 1, 2, 3, and 4 seconds between transient connection/timeout failures (including Redis loading); exhaustion fails startup. Authentication, authorization, and configuration errors fail immediately. Disabled broker/worker health is `n/a`, queue actions return 503, and cache invalidation requires an explicit `CACHE_REDIS_URL` to remain active. Independent worker/cron processes must be stopped separately.
- Core queue/cache and frontend cache Redis clients use redis-py's default RESP3 with `MaintNotificationsConfig(enabled=False)`. Worker/cron connections explicitly use RESP2 as well: RQ drops maintenance settings when rebuilding scheduler and spawned-worker connections, but preserves the protocol. This prevents unsupported maintenance-notification probes on Redis Open Source and leaves managed Redis Smart Client Handoffs unused.
- Scheduler query defaults, UTC normalization, and display serialization live in Pydantic models in `src/models/models/scheduler.py`. Queue failure diagnostics use a static message allowlist keyed by the persisted task reason, loaded in one database query. Never expose RQ exception text, arbitrary historical result messages, task data, raw provider responses, or private checkpoint configuration. Missing/malformed results use an explicit fallback with the worker-log reference.
- Core owns `rq:cron:def`: startup treats current source/bot/housekeeping specs as an allowlist and removes other persisted definitions and artifacts.
- Cron rebuilds empty Redis through authenticated Core recovery without clearing newly queued work; pending jobs are disposable. See [Redis Runtime State](redis-runtime-state.md).

Bot failure filters and menu counts also include failed endpoint probes; execution history remains independent. See [LLM Endpoints](llm-endpoints.md#endpoint-checks).

## Entry Points and Coverage

`src/frontend/frontend/views/admin_views/scheduler_views.py`, `src/frontend/frontend/templates/schedule/`, `src/core/core/managers/queue_manager.py`, `src/core/core/api/config.py`, `src/core/core/service/dashboard.py`, `src/core/core/service/task.py`; contracts in `src/models/models/admin.py` and `src/models/models/task.py`.

Tests: `src/frontend/tests/unit/views/test_scheduler.py`, `src/frontend/tests/playwright/test_e2e_admin.py`, `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`, `src/core/tests/application/admin_console/configuration/test_config_api.py`. Redis startup readiness and disabled-queue behavior: `src/core/tests/application/admin_console/configuration/test_queue_manager_schedules.py`. Retain dashboard-count versus Scheduled Jobs aggregate consistency coverage.

Completed Runs search/outcome preservation is covered by the existing admin dashboard browser workflow. Core's `src/core/tests/application/user_workspace/test_user_tasks.py` covers terminal-only history, background jobs, filtering, and payload redaction; avoid duplicating those contracts with markup-only tests.
