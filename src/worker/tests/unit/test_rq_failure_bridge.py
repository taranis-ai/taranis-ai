# pyright: reportMissingParameterType=false

from typing import cast

from rq.job import Job
from rq.timeouts import JobTimeoutException

from worker import rq_failure_bridge


class DummyJob:
    def __init__(self, job_id="job-1", *, meta=None, func_name="worker.collectors.collector_tasks.collector_task"):
        self.id = job_id
        self.meta = {} if meta is None else meta
        self.func_name = func_name


def test_timeout_exception_persists_synthetic_failure(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            captured["read_url"] = url
            return None

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"task": "collector_task", "user_id": "user-1", "worker_id": "source-1", "worker_type": "rss_collector"}))

    result = rq_failure_bridge.rq_failure_exception_handler(
        job,
        JobTimeoutException,
        JobTimeoutException("too slow"),
        None,
    )

    assert result is True
    assert captured["read_url"] == "/tasks/job-1"
    assert captured["args"] == ("job-1", "collector_task", "FAILURE")
    assert captured["kwargs"]["user_id"] == "user-1"
    assert captured["kwargs"]["worker_id"] == "source-1"
    assert captured["kwargs"]["worker_type"] == "rss_collector"
    assert captured["kwargs"]["result"] == {
        "message": "too slow",
        "reason": "job_timeout",
        "retryable": True,
        "data": {"exception_type": "JobTimeoutException", "message": "too slow"},
    }


def test_generic_exception_persists_synthetic_failure(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            return None

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"task": "presenter_task", "worker_id": "product-1", "worker_type": "pdf_presenter"}))

    rq_failure_bridge.rq_failure_exception_handler(
        job,
        RuntimeError,
        RuntimeError("boom"),
        None,
    )

    assert captured["args"] == ("job-1", "presenter_task", "FAILURE")
    assert captured["kwargs"]["result"]["reason"] == "job_failed"
    assert captured["kwargs"]["result"]["retryable"] is False


def test_killed_work_horse_persists_synthetic_failure(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            return None

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"task": "connector_task", "worker_id": "connector-1", "worker_type": "misp_connector"}))

    rq_failure_bridge.rq_work_horse_killed_handler(job, 111, 9, None)

    assert captured["args"] == ("job-1", "connector_task", "FAILURE")
    assert captured["kwargs"]["result"] == {
        "message": "Work horse killed for job job-1",
        "reason": "work_horse_killed",
        "retryable": True,
        "data": {"retpid": 111, "ret_val": 9},
    }


def test_bridge_skips_when_terminal_task_result_exists(monkeypatch):
    class FakeCoreApi:
        def api_get(self, url):
            return {"status": "FAILURE"}

        def save_task_result(self, *args, **kwargs):
            raise AssertionError("save_task_result should not be called")

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"task": "collector_task"}))

    assert rq_failure_bridge.rq_failure_exception_handler(job, RuntimeError, RuntimeError("boom"), None) is True


def test_bridge_persists_failure_when_terminal_probe_raises(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            raise RuntimeError("probe failed")

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"task": "collector_task"}))

    assert rq_failure_bridge.rq_failure_exception_handler(job, RuntimeError, RuntimeError("boom"), None) is True
    assert captured["args"] == ("job-1", "collector_task", "FAILURE")
    assert captured["kwargs"]["result"]["reason"] == "job_failed"


def test_bridge_uses_func_name_fallback_when_meta_task_missing(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            return None

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(Job, DummyJob(meta={"worker_id": "source-1", "worker_type": "rss_collector"}))

    rq_failure_bridge.rq_failure_exception_handler(job, RuntimeError, RuntimeError("boom"), None)

    assert captured["args"] == ("job-1", "collector_task", "FAILURE")


def test_bridge_normalizes_meta_strings_and_fetch_single_news_item_fallback(monkeypatch):
    captured = {}

    class FakeCoreApi:
        def api_get(self, url):
            return None

        def save_task_result(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return True

    monkeypatch.setattr(rq_failure_bridge, "CoreApi", FakeCoreApi)

    job = cast(
        Job,
        DummyJob(
            meta={"task": "   ", "user_id": " user-1 ", "worker_id": " source-1 ", "worker_type": "   "},
            func_name="worker.collectors.collector_tasks.fetch_single_news_item",
        ),
    )

    rq_failure_bridge.rq_failure_exception_handler(job, RuntimeError, RuntimeError("boom"), None)

    assert captured["args"] == ("job-1", "collector_task", "FAILURE")
    assert captured["kwargs"]["user_id"] == "user-1"
    assert captured["kwargs"]["worker_id"] == "source-1"
    assert captured["kwargs"]["worker_type"] is None
