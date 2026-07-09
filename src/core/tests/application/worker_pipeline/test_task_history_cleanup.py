import uuid
from datetime import datetime, timedelta, timezone

from core.config import Config
from core.model.task import Task as TaskModel


def test_task_history_cleanup_deletes_old_rows_regardless_of_type(app, client, api_header, monkeypatch):
    old_job_id = f"old-task-{uuid.uuid4().hex}"
    new_job_id = f"new-task-{uuid.uuid4().hex}"

    old_payload = {
        "id": old_job_id,
        "task": "collector_task",
        "worker_id": "old-worker",
        "worker_type": "simple_web_collector",
        "result": {"message": "old", "reason": None, "retryable": False, "data": None},
        "status": "SUCCESS",
    }
    new_payload = {
        "id": new_job_id,
        "task": "bot_task",
        "worker_id": "new-worker",
        "worker_type": "WORDLIST_BOT",
        "result": {"message": "new", "reason": None, "retryable": False, "data": None},
        "status": "FAILURE",
    }

    try:
        assert client.post("/api/tasks", json=old_payload, headers=api_header).status_code == 200
        assert client.post("/api/tasks", json=new_payload, headers=api_header).status_code == 200

        monkeypatch.setattr(Config, "TASK_HISTORY_RETENTION_DAYS", 7)

        with app.app_context():
            old_task = TaskModel.get(old_job_id)
            new_task = TaskModel.get(new_job_id)
            assert old_task is not None
            assert new_task is not None
            old_task.last_run = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8)
            new_task.last_run = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=6)
            from core.managers.db_manager import db

            db.session.commit()

        response = client.post("/api/worker/tasks/history/cleanup", headers=api_header)

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["message"] == "Task history cleanup completed"
        assert payload["deleted"] >= 1
        assert isinstance(payload["cutoff"], str)
        assert payload["retention_days"] == 7

        with app.app_context():
            assert TaskModel.get(old_job_id) is None
            assert TaskModel.get(new_job_id) is not None
    finally:
        with app.app_context():
            if TaskModel.get(old_job_id):
                TaskModel.delete(old_job_id)
            if TaskModel.get(new_job_id):
                TaskModel.delete(new_job_id)
