# Worker Task Notifications

## When To Load
Worker-backed frontend actions, task queue notifications, OSINT source collect, bot execute, word-list gather, product render, product publish, `/health`, and no-worker warning behavior.

## Expected Behavior
Worker-backed actions still report queue success when core accepts the job. If core health reports `workers: down`, the frontend shows a warning that the task was queued but may not be processed until a worker starts.

## Code Paths
Frontend notification handling lives in `frontend.views.base_view.BaseView.render_worker_task_notification`. Core health is read through `frontend.data_persistence.DataPersistenceLayer.get_core_health`.

## Data Flow
The frontend posts the worker-backed action to core. On a successful response, it reads cached `/health`; only `services.workers == "down"` changes the notification from success to warning.

## Testing
Use `cd src/frontend && uv run pytest tests/unit/views/test_worker_task_notifications.py` for focused coverage.

## Pitfalls
Do not change core queue endpoint status codes for this behavior. A missing or failed health check should keep the original task notification.
