import core.managers.queue_manager as qm_module
import core.model.task as task_module
from core.api.config import OSINTSourcePreview


class _FakeQueueManager:
    def __init__(self, get_task_result, preview_result=None):
        self._get_task_result = get_task_result
        self._preview_result = preview_result

    def get_task(self, task_id):
        return self._get_task_result(task_id)

    def preview_osint_source(self, source_id):
        if self._preview_result is None:
            raise AssertionError("preview should not be re-enqueued")
        return self._preview_result


def test_preview_response_uses_live_rq_status_without_requeue(monkeypatch):
    task_id = "source_preview_123"

    fake_qm = _FakeQueueManager(get_task_result=lambda tid: ({"id": tid, "status": "STARTED"}, 202))
    monkeypatch.setattr(task_module.Task, "get", staticmethod(lambda preview_task_id: None))
    monkeypatch.setattr(qm_module, "queue_manager", fake_qm, raising=False)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 202
    assert response == {"id": task_id, "status": "STARTED"}


def test_preview_response_falls_back_to_enqueue_when_job_missing(monkeypatch):
    task_id = "source_preview_123"
    scheduled_response = {"message": "Preview for source 123 scheduled", "id": task_id, "status": "STARTED"}

    fake_qm = _FakeQueueManager(
        get_task_result=lambda tid: ({"error": "Task not found"}, 404),
        preview_result=(scheduled_response, 201),
    )
    monkeypatch.setattr(task_module.Task, "get", staticmethod(lambda preview_task_id: None))
    monkeypatch.setattr(qm_module, "queue_manager", fake_qm, raising=False)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 201
    assert response == scheduled_response


def test_preview_response_reenqueues_failed_job(monkeypatch):
    task_id = "source_preview_123"
    scheduled_response = {"message": "Preview for source 123 scheduled", "id": task_id, "status": "STARTED"}

    fake_qm = _FakeQueueManager(
        get_task_result=lambda tid: ({"id": tid, "status": "FAILURE", "error": "collector crashed"}, 500),
        preview_result=(scheduled_response, 201),
    )
    monkeypatch.setattr(task_module.Task, "get", staticmethod(lambda preview_task_id: None))
    monkeypatch.setattr(qm_module, "queue_manager", fake_qm, raising=False)

    response, status = OSINTSourcePreview.get_osint_source_preview_response("123")

    assert status == 201
    assert response == scheduled_response
