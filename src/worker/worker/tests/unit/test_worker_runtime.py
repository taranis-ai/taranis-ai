from types import SimpleNamespace

from worker.worker_runtime import persist_work_horse_killed_failure


def test_persist_work_horse_killed_failure_reports_failure(monkeypatch):
    recorded = {}

    class DummyApi:
        def save_task_result(self, job_id, task_name, result, status, *, worker_id=None, worker_type=None):
            recorded["payload"] = {
                "id": job_id,
                "task": task_name,
                "result": result,
                "status": status,
                "worker_id": worker_id,
                "worker_type": worker_type,
            }
            return True

    monkeypatch.setattr("worker.worker_runtime.CoreApi", lambda: DummyApi())

    job = SimpleNamespace(
        id="job-123",
        meta={
            "task_submission": {
                "task": "collector_task",
                "worker_id": "source-1",
                "worker_type": "collector_task",
            }
        },
    )

    persist_work_horse_killed_failure(job, 456, 256, None)

    assert recorded["payload"] == {
        "id": "job-123",
        "task": "collector_task",
        "result": {
            "reason": "work_horse_killed",
            "retpid": 456,
            "ret_val": 256,
        },
        "status": "FAILURE",
        "worker_id": "source-1",
        "worker_type": "collector_task",
    }


def test_persist_work_horse_killed_failure_includes_signal(monkeypatch):
    recorded = {}

    class DummyApi:
        def save_task_result(self, job_id, task_name, result, status, *, worker_id=None, worker_type=None):
            recorded["result"] = result
            return True

    monkeypatch.setattr("worker.worker_runtime.CoreApi", lambda: DummyApi())

    job = SimpleNamespace(
        id="job-456",
        meta={
            "task_submission": {
                "task": "collector_task",
                "worker_id": "source-2",
                "worker_type": "collector_task",
            }
        },
    )

    persist_work_horse_killed_failure(job, 789, 15, None)

    assert recorded["result"] == {
        "reason": "work_horse_killed",
        "retpid": 789,
        "ret_val": 15,
        "signal": 15,
    }


def test_persist_work_horse_killed_failure_skips_invalid_metadata(monkeypatch):
    recorded = {"called": False}

    class DummyApi:
        def save_task_result(self, job_id, task_name, result, status, *, worker_id=None, worker_type=None):
            recorded["called"] = True
            return True

    monkeypatch.setattr("worker.worker_runtime.CoreApi", lambda: DummyApi())

    job = SimpleNamespace(
        id="job-789",
        meta={
            "task_submission": {
                "task": "collector_task",
                "worker_id": 123,
                "worker_type": "collector_task",
            }
        },
    )

    persist_work_horse_killed_failure(job, 1, 1, None)

    assert recorded["called"] is False
