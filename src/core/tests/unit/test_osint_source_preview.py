from unittest.mock import Mock

from core.api import config as config_api
from core.api.config import OSINTSourcePreview


def test_preview_response_uses_live_rq_status_without_requeue(monkeypatch):
    task_id = "source_preview_123"
    queue_manager = Mock()
    queue_manager.get_task.return_value = {"id": task_id, "status": "STARTED"}, 202

    monkeypatch.setattr(config_api.task.Task, "get", lambda preview_task_id: None)
    monkeypatch.setattr(config_api.queue_manager, "queue_manager", queue_manager, raising=False)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 202
    assert response == {"id": task_id, "status": "STARTED"}
    queue_manager.preview_osint_source.assert_not_called()


def test_preview_response_requeues_when_task_not_found(monkeypatch):
    task_id = "source_preview_123"
    scheduled_response = {"message": "Preview for source 123 scheduled", "id": task_id, "status": "STARTED"}
    queue_manager = Mock()
    queue_manager.get_task.return_value = {"error": "Task not found"}, 404
    queue_manager.preview_osint_source.return_value = scheduled_response, 201

    monkeypatch.setattr(config_api.task.Task, "get", lambda preview_task_id: None)
    monkeypatch.setattr(config_api.queue_manager, "queue_manager", queue_manager, raising=False)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 201
    assert response == scheduled_response
    queue_manager.preview_osint_source.assert_called_once_with("123")


def test_preview_response_uses_persisted_failure_without_requeue(monkeypatch):
    persisted_failure = {
        "id": "source_preview_123",
        "status": "FAILURE",
        "result": {"message": "worker died", "reason": "work_horse_killed", "retryable": True, "data": {"retpid": 123, "ret_val": 9}},
    }

    class FakeTaskResult:
        def to_dict(self):
            return persisted_failure

    monkeypatch.setattr(config_api.task.Task, "get", lambda preview_task_id: FakeTaskResult())

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 200
    assert response == persisted_failure
