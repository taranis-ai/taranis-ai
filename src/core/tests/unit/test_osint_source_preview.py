from types import SimpleNamespace

from core.api import config


def test_preview_response_uses_live_rq_status_without_requeue(monkeypatch):
    task_id = "source_preview_123"

    def _fail_requeue(*_args, **_kwargs):
        raise AssertionError("preview should not be re-enqueued")

    queue_manager_stub = SimpleNamespace(
        get_task=lambda preview_task_id: ({"id": preview_task_id, "status": "STARTED"}, 202),
        preview_osint_source=_fail_requeue,
    )

    monkeypatch.setattr(config.task.Task, "get", lambda preview_task_id: None)
    monkeypatch.setattr(config.queue_manager, "queue_manager", queue_manager_stub, raising=False)

    response, status = config.OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 202
    assert response == {"id": task_id, "status": "STARTED"}

    task_id = "source_preview_123"
    scheduled_response = {"message": "Preview for source 123 scheduled", "id": task_id, "status": "STARTED"}

    monkeypatch.setattr(config.task.Task, "get", lambda preview_task_id: None)
    queue_manager_stub.get_task = lambda preview_task_id: ({"error": "Task not found"}, 404)
    queue_manager_stub.preview_osint_source = lambda source_id: (scheduled_response, 201)

    response, status = config.OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 201
    assert response == scheduled_response
