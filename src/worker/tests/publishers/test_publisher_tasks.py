import pytest

from worker.publishers import publisher_tasks
from worker.publishers.execution_context import PublisherNetworkTimeout


def _email_publisher_config():
    return {
        "id": "publisher-1",
        "type": "email_publisher",
        "parameters": {
            "SMTP_SERVER_ADDRESS": "smtp.example.test",
            "EMAIL_SENDER": "sender@example.test",
            "EMAIL_RECIPIENT": "recipient@example.test",
        },
    }


def test_publisher_task_persists_phase_metadata(monkeypatch, recording_core_api_factory, recording_job_factory, recording_publisher_factory):
    job = recording_job_factory(timeout=60)
    core_api = recording_core_api_factory(publisher=_email_publisher_config())
    publisher = recording_publisher_factory()
    monkeypatch.setattr(publisher_tasks, "get_current_job", lambda: job)
    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core_api)
    monkeypatch.setattr(publisher_tasks, "_get_publisher_impl", lambda _publisher_type: publisher)

    assert publisher_tasks.publisher_task.__wrapped__("product-1", "publisher-1") == {"message": "published"}
    diagnostics = job.meta["publisher_diagnostics"]
    assert diagnostics["product_id"] == "product-1"
    assert diagnostics["publisher_id"] == "publisher-1"
    assert diagnostics["publisher_type"] == "email_publisher"
    assert diagnostics["phase"] == "prepare"
    assert job.meta["user_id"] == "user-1"


@pytest.mark.parametrize(
    ("error", "expected_message", "expected_reason"),
    [
        (RuntimeError("secret-host.example"), "Publisher task failed", "publisher_failed"),
        (
            PublisherNetworkTimeout("email_publisher", "send"),
            "Email publisher timed out during send",
            "publisher_network_timeout",
        ),
    ],
)
def test_publisher_task_persists_sanitized_failures(
    monkeypatch,
    recording_core_api_factory,
    recording_job_factory,
    recording_publisher_factory,
    error,
    expected_message,
    expected_reason,
    caplog,
):
    job = recording_job_factory()
    core_api = recording_core_api_factory(publisher=_email_publisher_config())
    publisher = recording_publisher_factory(error=error)
    monkeypatch.setattr(publisher_tasks, "get_current_job", lambda: job)
    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core_api)
    monkeypatch.setattr(publisher_tasks, "_get_publisher_impl", lambda _publisher_type: publisher)

    with pytest.raises(type(error)):
        publisher_tasks.publisher_task.__wrapped__("product-1", "publisher-1")

    failure = core_api.put_calls[-1]["json"]["result"]
    assert failure.message == expected_message
    assert failure.reason == expected_reason
    assert "secret-host" not in str(failure.model_dump())
    assert "secret-host" not in caplog.text
