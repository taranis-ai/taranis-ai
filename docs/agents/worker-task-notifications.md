# Worker Task Notifications

## When To Load
Worker-backed frontend actions, task queue notifications, OSINT source collect, bot execute, word-list gather, product render, product publish, `/health`, and no-worker warning behavior.

## Expected Behavior
Worker-backed actions still report queue success when core accepts the job. If core health reports `workers: down`, the frontend shows a warning that the task was queued but may not be processed until a worker starts. Final task failures are not pushed into that enqueue notification, but persisted task/status views reflect actual RQ-level failures such as exceptions, timeouts, and killed workhorses. For user-triggered runs, the persisted task row also carries the authenticated `user_id`; scheduler-driven runs leave it empty.
Task history is retained globally by the daily `cleanup_task_history` housekeeping job. The retention window comes from the core `TASK_HISTORY_RETENTION_DAYS` environment variable and does not vary by task type or worker family.
The My Tasks page lists only completed persisted results belonging to the authenticated user, including successful OSINT source previews with `PREVIEW` status. It does not query Redis or display queued and running jobs; enqueue notifications remain the immediate acknowledgement for those states.

Jobs carrying an authenticated `user_id` are enqueued at the front of their functional RQ queue. User-triggered jobs therefore run in last-in, first-out order within that queue, while scheduler-driven and other background jobs retain normal first-in, first-out ordering. User attribution and front-of-queue priority propagate through deferred dependencies and post-collection bot scheduling.

## Code Paths
Frontend notification handling lives in `frontend.views.base_view.BaseView.render_worker_task_notification`. Core health is read through `frontend.data_persistence.DataPersistenceLayer.get_core_health`.
The user task route lives in `frontend.views.user_views.UserTaskView`; its user-scoped core endpoint is `GET /tasks/user`.

## Data Flow
The frontend posts the worker-backed action to core. On a successful response, it reads cached `/health`; only `services.workers == "down"` changes the notification from success to warning. Core includes the authenticated user in the queued job metadata for manual runs, derives RQ's `at_front` option from that metadata, and worker-side task persistence copies the user onto the task row. Worker-triggered follow-up requests forward the current job's user metadata so downstream jobs retain the same behavior. The history-cleanup worker records core HTTP failures as `core_http_error`, including the status and response body; transport failures are recorded as `core_transport_error`. Separately, core stores synthetic task failures from worker-level RQ hooks when a job dies before task code can call `save_task_result(...)`, and from the background reconciler when a run is missed or stalls before any worker-side persistence can happen.

## Testing
Use `cd src/frontend && uv run pytest tests/unit/views/test_worker_task_notifications.py` for focused coverage.
Use `cd src/frontend && uv run pytest tests/unit/views/test_user_task_view.py` and the core user-task tests for the completed-results view.

## Pitfalls
Do not change core queue endpoint status codes for this behavior. A missing or failed health check should keep the original task notification. The enqueue notification is still only about scheduling; failure visibility for admin/source/bot/render status comes from persisted task rows, not a second frontend polling path.

The user endpoint must always derive ownership from the authenticated user, exclude scheduler and other-user rows, and omit task-specific `result.data`. Search is limited to visible relational fields and must not match `result.data` or other serialized result content.

Front-of-queue priority is local to each functional queue. Workers check enabled queues in this priority order: presenters, publishers, connectors, misc, bots, collectors. A dedicated collector worker is unaffected because it only subscribes to collectors. An already running job is never preempted.

RQ promotes jobs created with `enqueue_at` when they become due without waiting for unfinished `depends_on` jobs. Scheduled user jobs retain front-of-queue promotion, but callers must not use scheduled dependencies to model execution ordering.
