# Worker Task Notifications

Load for: Worker-backed actions, queue warnings/priority, task results, `/health`, My Tasks, or history retention.

## Queue and Result Contracts

Task entry points and RQ failure hooks own their HTTP session scope, including result persistence on error. See [HTTP Client Lifetimes](http-clients.md) for cleanup and no-retry service behavior.

- With `QUEUE_ENABLED=false`, core skips queue connections and scheduling; broker/worker health is `n/a` and queue actions are unavailable (503). Source collection/preview and bot execution/chains reject disabled queues before source/bot validation or graph construction. Enabled queues require Redis at startup.
- Accepted jobs report queue success. Only cached core health `services.workers == "down"` changes this to a queued-but-no-worker warning; failed/missing health checks retain the original notice. Do not change queue endpoint status codes or poll for final failures through this notification.
- Story AI actions resolve bot types to the first configured instance by index; explicit UUIDs select that bot. `generate_tags` queues Wordlist → IOC → NER for the selected story. Check write access first; any missing/disabled/invalid bot or endpoint rejects dispatch. Return only notifications with Core’s status, preserving the editor on errors. Assess E2E temporarily enables and restores its LLM endpoint.
- Connector pulls return the queue manager's response and HTTP status directly: success means scheduled, and disabled queues return 503. News-item URL fetches preserve queue error tuples through `StoryService` and the Assess endpoint. These API contracts are covered in the core configuration workflow and disabled-queue startup tests.
- Authenticated runs, including auto-render after product edits, carry `user_id`; scheduler runs do not. Propagate attribution through dependencies and post-collection bots.
- User jobs enqueue at the front of their functional queue (LIFO); background jobs remain FIFO. Workers check presenters, publishers, connectors, misc, bots, then collectors. Priority does not preempt running jobs or affect workers subscribed to other queues.
- RQ `enqueue_at` promotion does not wait for unfinished dependencies. Scheduled user jobs keep front priority, but scheduled dependencies cannot model execution ordering.
- Persist actual RQ failures, including timeouts/killed workhorses. Worker hooks synthesize results when task code cannot save; the reconciler covers missed/stalled runs. LLM task/pipeline handlers preserve `job_timeout` and distinguish request timeout, invalid output, and failed tag uploads (`tag_save_failed`) with curated messages.
- Bot checkpoint continuation follows [Bot Run Order DAG](bot-run-order-dag.md). Interim attempts do not create completed failure results; My Tasks receives only the final success or terminal failure. RQ results and worker logs retain attempt evidence.
- Publisher network failures persist a curated message, publisher/product IDs, publisher type, and the operation from the publisher exception. Operations are logged normally without phase metadata or timing state. RQ deadlines and killed workhorses use generic static failures; deduplication and user attribution remain intact. User-visible messages never contain raw exception text.
- Publisher handlers and cleanup propagate RQ timeout exceptions to the failure bridge. Network timeout classification requires a timeout exception (direct or wrapped); elapsed time alone does not turn an ordinary failure into a timeout.
- Successful user-attributed staged bot results also publish story-scoped completion events for targeted editor refreshes; see [Realtime Events](realtime-events.md#story-editor-ai-results).
- Successful presenter results publish user-scoped `product.rendered` after commit; notification failure cannot change task success. See [Realtime Events](realtime-events.md).
- MISP results reflect completed sync/proposal operations, not dispatch success. Entire failures use one connector failure path; curated reasons include `connector_not_found` and `connector_type_missing`.
- Bot transport failures use retryable `bot_service_unavailable` so dependents do not run. Log the transport error server-side, retain the curated exception's originating traceback, and suppress the underlying HTTP exception chain from displayed failures.

Endpoint probe health is stored separately from execution history; see [LLM Endpoints](llm-endpoints.md#endpoint-checks).

## History and UI

Committed pipeline steps produce separate per-bot results with the pipeline owner and completion timestamp; they also appear in My Tasks and the scheduler Completed Runs view.

My Tasks combines owned RQ queued/deferred/delayed/running jobs with persisted terminal results, including successful `PREVIEW` results. RQ metadata is projected through an allowlist; story bot job names identify the configured action and story ID. Workers preserve that public name in terminal submissions, including failure hooks and committed pipeline stages; history searches the name after the RQ job expires. The nullable `task.name` column is added by the automatic migration; older history remains unnamed. Deploy Core before updated workers, which submit the new field. The additive column can remain during rollback. Never expose checkpoints, job arguments, or task `result.data`; search only visible fields. Terminal results suppress stale live entries for the same execution, while older results remain visible during a new execution. Redis outages or disabled queues leave completed history available. Sorting/pagination merge live rows with a bounded SQL history window. This differs from [Notification Center](notification-center.md) history.

My Tasks refreshes on owner-scoped `task.changed` SSE events, including when the visible table has no live rows. Initial connection and reconnect resync recover missed transitions. It uses the existing authenticated EventSource and bypasses the frontend list cache. The shared `macros/live_table.html` controller coalesces bursts for 300 ms and retains the final event until navigation finishes, resolving the latest table query when the refresh starts. Search, sorting, and pagination replace pending refreshes through the same HTMX queue. There is no polling; an explained Refresh control appears only while realtime is disabled, connecting, or disconnected. Unavailable live task state retains completed history with a retry notice and keeps Refresh visible even when the event stream is connected. Story action acceptance invalidates task/scheduler list caches.

Live jobs are fetched in one Redis pipeline and use the status from that snapshot; missing jobs are skipped. Core queues project ownership into the RQ job hash atomically with job creation. User task reads use that small field before fetching full owned jobs; legacy/cron jobs read metadata once and cache ownership in the existing hash without recreating expired jobs. The field expires with the job, and ownership is rechecked on fetched metadata. SQL history and the live-row merge sort missing worker types as empty strings and use binary text ordering (PostgreSQL `C`, SQLite `BINARY`) for fields and ID tie-breaks so pagination agrees with Python.

Daily `cleanup_task_history` applies global `TASK_HISTORY_RETENTION_DAYS` across task families. Cleanup records core HTTP/transport failures as `core_http_error`/`core_transport_error`.

Source-detail Collect/Bot Run return notifications; Collect All/Update Wordlists replace their table containers. Follow [shared frontend swap rules](frontend-development.md).

## Code and Tests

`BaseView.render_worker_task_notification` in `src/frontend/frontend/views/base_view.py`; `DataPersistenceLayer.get_core_health` in `src/frontend/frontend/data_persistence.py`; `UserTaskView` in `src/frontend/frontend/views/user_views.py`; user endpoint `GET /tasks/user`.

Tests: `src/core/tests/application/user_workspace/test_user_tasks.py`, `src/frontend/tests/playwright/test_e2e_rq_tasks.py`, `src/frontend/tests/unit/views/test_worker_task_notifications.py`, `src/frontend/tests/unit/views/test_user_task_view.py`, `src/worker/tests/connectors/test_misp_connector.py`, `src/worker/tests/bots/test_bot_tasks.py`.
