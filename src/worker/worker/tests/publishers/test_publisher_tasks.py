import pytest

from worker.publishers import publisher_tasks


class DummyJob:
    id = "publisher-job-123"


def test_publisher_task_persists_success_payload(monkeypatch, recording_core_api_factory, recording_publisher_factory):
    core_api = recording_core_api_factory()
    publisher = recording_publisher_factory(result={"message": "Published to email", "delivery_id": "delivery-1"})

    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core_api)
    monkeypatch.setattr(publisher_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(publisher_tasks, "_get_publisher_impl", lambda publisher_type: publisher)

    result = publisher_tasks.publisher_task("prod-123", "pub-1")

    assert result == {"message": "Published to email", "delivery_id": "delivery-1"}
    assert core_api.put_calls[-1] == {
        "url": "/tasks",
        "json": {
            "id": "publisher-job-123",
            "task": "publisher_task",
            "worker_id": "pub-1",
            "worker_type": "email_publisher",
            "result": {
                "message": "Published to email",
                "reason": None,
                "retryable": False,
                "data": {
                    "product_id": "prod-123",
                    "publisher_id": "pub-1",
                    "message": "Published to email",
                    "delivery_id": "delivery-1",
                },
            },
            "status": "SUCCESS",
        },
    }


def test_publisher_task_fails_when_publisher_returns_none(monkeypatch, recording_core_api_factory, recording_publisher_factory):
    core_api = recording_core_api_factory()
    publisher = recording_publisher_factory(result=None)

    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core_api)
    monkeypatch.setattr(publisher_tasks, "get_current_job", lambda: DummyJob())
    monkeypatch.setattr(publisher_tasks, "_get_publisher_impl", lambda publisher_type: publisher)

    with pytest.raises(RuntimeError, match="Publisher pub-1 returned no result"):
        publisher_tasks.publisher_task("prod-123", "pub-1")

    assert core_api.put_calls[-1] == {
        "url": "/tasks",
        "json": {
            "id": "publisher-job-123",
            "task": "publisher_task",
            "worker_id": "pub-1",
            "worker_type": "email_publisher",
            "result": {
                "message": "Publisher pub-1 returned no result",
                "reason": "publisher_failed",
                "retryable": False,
                "data": {"product_id": "prod-123", "publisher_id": "pub-1"},
            },
            "status": "FAILURE",
        },
    }
