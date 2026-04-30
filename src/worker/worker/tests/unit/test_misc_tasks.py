from models.task_submission_meta import build_worker_task_payload

from worker.misc import misc_tasks


class DummyJob:
    id = "job-123"


def test_cleanup_token_blacklist_reports_task(monkeypatch):
    recorded = {}

    class DummyApi:
        def save_task_result(self, job_id, task_name, result, status, *, worker_id=None, worker_type=None):
            recorded["url"] = "/tasks"
            recorded["payload"] = {
                "id": job_id,
                "task": task_name,
                "worker_id": worker_id,
                "worker_type": worker_type,
                "result": result,
                "status": status,
            }
            return True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())

    message = misc_tasks.cleanup_token_blacklist(build_worker_task_payload("cleanup_token_blacklist", "cleanup_token_blacklist"))

    assert message == "Token blacklist cleanup triggered"
    assert recorded["url"] == "/tasks"
    assert recorded["payload"] == {
        "id": DummyJob.id,
        "task": "cleanup_token_blacklist",
        "worker_id": "cleanup_token_blacklist",
        "worker_type": "cleanup_token_blacklist",
        "result": "Token blacklist cleanup triggered",
        "status": "SUCCESS",
    }


def test_cleanup_token_blacklist_reschedules_when_requested(monkeypatch):
    ran = {"rescheduled": False}

    class DummyApi:
        def save_task_result(self, job_id, task_name, result, status, *, worker_id=None, worker_type=None):
            return True

    def mark_rescheduled():
        ran["rescheduled"] = True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(misc_tasks, "_reschedule_cleanup", mark_rescheduled)

    misc_tasks.cleanup_token_blacklist(
        build_worker_task_payload(
            "cleanup_token_blacklist",
            "cleanup_token_blacklist",
            "cleanup_token_blacklist",
            {"reschedule": True},
        )
    )

    assert ran["rescheduled"] is True
