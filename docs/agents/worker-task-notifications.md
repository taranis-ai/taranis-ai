# Worker Task Notifications

## When To Load
Worker-backed frontend actions, task queue notifications, OSINT source collect, bot execute, word-list gather, product render, product publish, `/health`, and no-worker warning behavior.

## Expected Behavior
Worker-backed actions still report queue success when core accepts the job. If core health reports `workers: down`, the frontend shows a warning that the task was queued but may not be processed until a worker starts. Final task failures are not pushed into that enqueue notification, but persisted task/status views now also reflect RQ-level failures such as timeouts and killed workhorses. A background reconciliation task also persists operational gaps that never reach worker hooks: `cron_missed`, `job_stalled_in_scheduled`, `job_stalled_in_queue`, and `job_abandoned_after_start`. For user-triggered runs, the persisted task row also carries the authenticated `user_id`; scheduler-driven runs leave it empty.

## Code Paths
Frontend notification handling lives in `frontend.views.base_view.BaseView.render_worker_task_notification`. Core health is read through `frontend.data_persistence.DataPersistenceLayer.get_core_health`.

## Data Flow
The frontend posts the worker-backed action to core. On a successful response, it reads cached `/health`; only `services.workers == "down"` changes the notification from success to warning. Core includes the authenticated user in the queued job metadata for manual runs, and worker-side task persistence copies that onto the task row. Separately, core stores synthetic task failures from worker-level RQ hooks when a job dies before task code can call `save_task_result(...)`, and from the background reconciler when a run is missed or stalls before any worker-side persistence can happen.

## Testing
Use `cd src/frontend && uv run pytest tests/unit/views/test_worker_task_notifications.py` for focused coverage.

## Pitfalls
Do not change core queue endpoint status codes for this behavior. A missing or failed health check should keep the original task notification. The enqueue notification is still only about scheduling; failure visibility for admin/source/bot/render status comes from persisted task rows, not a second frontend polling path.
