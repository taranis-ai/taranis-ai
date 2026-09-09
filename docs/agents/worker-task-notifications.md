# Worker Task Notifications

## When To Load

Worker-backed actions, queue warnings/priority, task results, `/health`, My Tasks, or history retention.

## Queue and Result Contracts

Task entry points and RQ failure hooks own their HTTP session scope, including result persistence on error. See [HTTP Client Lifetimes](http-clients.md) for cleanup and no-retry service behavior.

- Accepted jobs report queue success. Only cached core health `services.workers == "down"` changes this to a queued-but-no-worker warning; failed/missing health checks retain the original notice. Do not change queue endpoint status codes or poll for final failures through this notification.
- Authenticated runs, including auto-render after product edits, carry `user_id`; scheduler runs do not. Propagate attribution through dependencies and post-collection bots.
- User jobs enqueue at the front of their functional queue (LIFO); background jobs remain FIFO. Workers check presenters, publishers, connectors, misc, bots, then collectors. Priority does not preempt running jobs or affect workers subscribed to other queues.
- RQ `enqueue_at` promotion does not wait for unfinished dependencies. Scheduled user jobs keep front priority, but scheduled dependencies cannot model execution ordering.
- Persist actual RQ failures, including timeouts/killed workhorses. Worker hooks synthesize results when task code cannot save; the reconciler covers missed/stalled runs.
- Successful presenter results publish user-scoped `product.rendered` after commit; notification failure cannot change task success. See [Realtime Events](realtime-events.md).
- MISP results reflect completed sync/proposal operations, not dispatch success. Entire failures use one connector failure path; curated reasons include `connector_not_found` and `connector_type_missing`.
- Bot transport failures use retryable `bot_service_unavailable` so dependents do not run. Log the transport error server-side, retain the curated exception's originating traceback, and suppress the underlying HTTP exception chain from displayed failures.

## History and UI

My Tasks lists only completed persisted results owned by the authenticated user, including successful `PREVIEW` results. It never queries Redis for queued/running jobs. Omit task `result.data`; search only visible relational fields, never serialized results. This differs from [Notification Center](notification-center.md) history.

Daily `cleanup_task_history` applies global `TASK_HISTORY_RETENTION_DAYS` across task families. Cleanup records core HTTP/transport failures as `core_http_error`/`core_transport_error`.

Source-detail Collect/Bot Run return notifications; Collect All/Update Wordlists replace their table containers. Follow [shared frontend swap rules](frontend-development.md).

## Entry Points and Coverage

`BaseView.render_worker_task_notification` in `src/frontend/frontend/views/base_view.py`; `DataPersistenceLayer.get_core_health` in `src/frontend/frontend/data_persistence.py`; `UserTaskView` in `src/frontend/frontend/views/user_views.py`; user endpoint `GET /tasks/user`.

Tests: `src/frontend/tests/unit/views/test_worker_task_notifications.py`, `src/frontend/tests/unit/views/test_user_task_view.py`, `src/worker/tests/connectors/test_misp_connector.py`, `src/worker/tests/bots/test_bot_api.py`, `src/worker/tests/bots/test_bot_tasks.py`.
