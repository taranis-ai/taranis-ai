from worker.misc import misc_tasks


class DummyJob:
    id = "job-123"


def test_cleanup_token_blacklist_reports_task(monkeypatch):
    recorded = {}

    class DummyApi:
        def api_put(self, url, payload):
            recorded["url"] = url
            recorded["payload"] = payload
            return {"status": "ok"}

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())

    message = misc_tasks.cleanup_token_blacklist()

    assert message == "Token blacklist cleanup triggered"
    assert recorded["url"] == "/worker/task-results"
    assert recorded["payload"] == {
        "id": DummyJob.id,
        "task": "cleanup_token_blacklist",
        "result": "Token blacklist cleanup triggered",
        "status": "SUCCESS",
    }


def test_cleanup_token_blacklist_reschedules_when_requested(monkeypatch):
    ran = {"rescheduled": False}

    class DummyApi:
        def api_put(self, url, payload):
            return {"status": "ok"}

    def mark_rescheduled():
        ran["rescheduled"] = True

    monkeypatch.setattr(misc_tasks, "CoreApi", lambda: DummyApi())
    monkeypatch.setattr(misc_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(misc_tasks, "_reschedule_cleanup", mark_rescheduled)

    misc_tasks.cleanup_token_blacklist(reschedule=True)

    assert ran["rescheduled"] is True
