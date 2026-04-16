import pytest

from worker.collectors import collector_tasks
from worker.config import Config


@pytest.fixture
def current_job(monkeypatch, mock_job):
    mock_job.meta = {}
    mock_job.save_meta = lambda: None
    monkeypatch.setattr(collector_tasks, "get_current_job", lambda: mock_job)
    return mock_job


def test_collector_task_missing_source_is_skipped(current_job, requests_mock):
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/osint-sources/source-missing",
        status_code=404,
        json={"error": "not found"},
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.collector_task("source-missing", manual=False)

    assert result == "Skipped collector task: Source with id source-missing not found"
    assert current_job.meta["status"] == "SKIPPED"
    assert current_job.meta["message"] == result

    put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(put_calls) == 1
    assert put_calls[0].json() == {
        "id": "test-job-123",
        "task": "collector_task",
        "worker_id": "source-missing",
        "worker_type": "collector_task",
        "result": result,
        "status": "SUCCESS",
    }
