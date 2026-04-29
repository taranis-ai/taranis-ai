from core.api.config import OSINTSourcePreview


def test_preview_response_uses_live_rq_status_without_requeue(monkeypatch):
    task_id = "source_preview_123"

    def _fail_requeue(*_args, **_kwargs):
        raise AssertionError("preview should not be re-enqueued")

    monkeypatch.setattr("core.api.config.task.Task.get", lambda preview_task_id: None)
    monkeypatch.setattr(
        "core.api.config.queue_manager.queue_manager.get_task",
        lambda preview_task_id: ({"id": preview_task_id, "status": "STARTED"}, 202),
    )
    monkeypatch.setattr("core.api.config.queue_manager.queue_manager.preview_osint_source", _fail_requeue)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 202
    assert response == {"id": task_id, "status": "STARTED"}


def test_preview_response_falls_back_to_enqueue_when_job_missing(monkeypatch):
    task_id = "source_preview_123"
    scheduled_response = {"message": "Preview for source 123 scheduled", "id": task_id, "status": "STARTED"}

    monkeypatch.setattr("core.api.config.task.Task.get", lambda preview_task_id: None)
    monkeypatch.setattr("core.api.config.queue_manager.queue_manager.get_task", lambda preview_task_id: ({"error": "Task not found"}, 404))
    monkeypatch.setattr(
        "core.api.config.queue_manager.queue_manager.preview_osint_source",
        lambda source_id: (scheduled_response, 201),
    )

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 201
    assert response == scheduled_response
