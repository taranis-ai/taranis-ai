from worker.misc import misc_tasks


class DummyJob:
    id = "job-123"


def test_cleanup_token_blacklist_reports_task(monkeypatch):
    recorded = {}

    class DummyApi:
        def save_task_result(self, job_id, task_name, status, *, worker_id=None, worker_type=None, result=None, **task_kwargs):
            recorded["url"] = "/tasks"
            recorded["payload"] = {
                "id": job_id,
                "task": task_name,
                "worker_id": worker_id,
                "worker_type": worker_type,
                "result": task_kwargs if result is None else result,
                "status": status,
            }
            return True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())

    message = misc_tasks.cleanup_token_blacklist()

    assert message == "Token blacklist cleanup triggered"
    assert recorded["url"] == "/tasks"
    assert recorded["payload"] == {
        "id": DummyJob.id,
        "task": "cleanup_token_blacklist",
        "worker_id": DummyJob.id,
        "worker_type": "cleanup_token_blacklist",
        "result": {
            "message": "Token blacklist cleanup triggered",
            "reason": None,
            "retryable": False,
            "data": None,
        },
        "status": "SUCCESS",
    }


def test_cleanup_token_blacklist_reschedules_when_requested(monkeypatch):
    ran = {"rescheduled": False}

    class DummyApi:
        def save_task_result(self, job_id, task_name, status, *, worker_id=None, worker_type=None, result=None, **task_kwargs):
            return True

    def mark_rescheduled():
        ran["rescheduled"] = True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(misc_tasks, "_reschedule_cleanup", mark_rescheduled)

    misc_tasks.cleanup_token_blacklist(reschedule=True)

    assert ran["rescheduled"] is True


def test_gather_word_list_persists_canonical_success_payload(monkeypatch):
    recorded = {}

    class DummyApi:
        def save_task_result(self, job_id, task_name, status, *, worker_id=None, worker_type=None, result=None, **task_kwargs):
            recorded["payload"] = {
                "id": job_id,
                "task": task_name,
                "worker_id": worker_id,
                "worker_type": worker_type,
                "result": task_kwargs if result is None else result,
                "status": status,
            }
            return True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(
        misc_tasks,
        "update_wordlist",
        lambda word_list_id: {
            "message": f"Word list {word_list_id} updated from remote source",
            "content": "alpha,beta",
            "content_type": "text/csv",
            "ignored": "value",
        },
    )

    result = misc_tasks.gather_word_list("word-list-1")

    assert result["message"] == "Word list word-list-1 updated from remote source"
    assert recorded["payload"] == {
        "id": DummyJob.id,
        "task": "gather_word_list",
        "worker_id": "word-list-1",
        "worker_type": "gather_word_list",
        "result": {
            "message": "Word list word-list-1 updated from remote source",
            "reason": None,
            "retryable": False,
            "data": {
                "word_list_id": "word-list-1",
                "content": "alpha,beta",
                "content_type": "text/csv",
            },
        },
        "status": "SUCCESS",
    }
    assert "message" not in recorded["payload"]["result"]["data"]
