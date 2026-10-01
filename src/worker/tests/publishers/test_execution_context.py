import pytest
from rq.timeouts import JobTimeoutException

from worker.publishers.execution_context import PublisherExecutionContext, publisher_network_phase


def test_execution_context_caps_timeout_and_preserves_task_metadata(recording_job_factory):
    job = recording_job_factory(timeout=40)
    context = PublisherExecutionContext(product_id="product-1", publisher_id="publisher-1", job=job)

    context.set_publisher_type("sftp_publisher")
    context.start_phase("upload")

    assert context.effective_network_timeout(30) == 20
    assert job.meta["task"] == "publisher_task"
    assert job.meta["user_id"] == "user-1"
    assert job.meta["publisher_diagnostics"] | {"task_started_at": "ignored", "phase_started_at": "ignored"} == {
        "task_started_at": "ignored",
        "phase_started_at": "ignored",
        "product_id": "product-1",
        "publisher_id": "publisher-1",
        "publisher_type": "sftp_publisher",
        "phase": "upload",
    }


def test_execution_context_uses_configured_timeout_without_job():
    context = PublisherExecutionContext(product_id="product-1", publisher_id="publisher-1")

    assert context.effective_network_timeout(30) == 30


def test_network_phase_does_not_replace_rq_timeout():
    with pytest.raises(JobTimeoutException), publisher_network_phase("upload", 0, "sftp_publisher"):
        raise JobTimeoutException("RQ deadline")
