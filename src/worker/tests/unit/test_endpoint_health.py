import pytest
from fakeredis import FakeRedis
from niquests.exceptions import ConnectionError
from rq import Retry
from rq.job import Job

from worker.config import Config
from worker.endpoint_health import check_endpoint


@pytest.mark.parametrize("api_format", ["responses", "chat_completions"])
def test_batch_endpoint_check_waits_for_inference(requests_mock, monkeypatch, api_format):
    config = {
        "name": "Batch probe",
        "base_url": "https://batch.test/api/v1",
        "model": "deepseek/deepseek-v4.1-flash:batch",
        "processing_mode": "openrouter_batch",
        "api_format": api_format,
        "api_key": "probe-key",
        "timeout": 10,
    }
    route = f"{Config.TARANIS_CORE_URL}/worker/endpoint-health/llm/test-id"
    requests_mock.get(route, json={"config": config})
    saved = requests_mock.post(route, json={"accepted": True})
    submitted = requests_mock.post(f"{config['base_url']}/batches", status_code=202, json={"id": "batch_probe", "status": "validating"})
    job = Job.create(check_endpoint, connection=FakeRedis())
    job.save()
    monkeypatch.setattr("worker.endpoint_health.get_current_job", lambda: job)
    assert isinstance(check_endpoint("llm", "test-id", "current-check"), Retry)
    assert saved.call_count == 0
    request_id = submitted.last_request.json()["requests"][0]["custom_id"]
    requests_mock.get(f"{config['base_url']}/batches/batch_probe", json={"status": "in_progress"})
    assert isinstance(check_endpoint("llm", "test-id", "current-check"), Retry)
    assert saved.call_count == 0
    body = (
        {"choices": [{"message": {"content": "OK"}}]}
        if api_format == "chat_completions"
        else {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]}
    )
    requests_mock.get(
        f"{config['base_url']}/batches/batch_probe",
        json={
            "status": "completed",
            "results": [{"custom_id": request_id, "response": {"status_code": 200, "body": body}}],
        },
    )
    check_endpoint("llm", "test-id", "current-check")
    assert saved.last_request.json() == {"check_id": "current-check", "healthy": True}
    assert submitted.call_count == 1
    assert "llm_batch_probe" not in job.meta


@pytest.mark.parametrize(
    ("kind", "config", "url", "result"),
    [
        (
            "llm",
            {"base_url": "http://model.test/v1", "api_format": "responses", "model": "test-model", "api_key": "test-secret", "timeout": 10},
            "http://model.test/v1/responses",
            {"status": "completed", "error": None, "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]},
        ),
        (
            "llm",
            {"base_url": "http://model.test/v1", "api_format": "chat_completions", "timeout": 10},
            "http://model.test/v1/chat/completions",
            {"choices": [{"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}]},
        ),
    ],
)
def test_endpoint_check_failure_and_recovery(requests_mock, kind, config, url, result):
    route = f"{Config.TARANIS_CORE_URL}/worker/endpoint-health/{kind}/test-id"
    requests_mock.get(route, json={"config": config})
    saved = requests_mock.post(route, json={"accepted": True})
    upstream = requests_mock.post(
        url,
        [
            {"exc": ConnectionError("private exception detail")},
            {"status_code": 401, "text": "private upstream detail"},
            {"json": {"unexpected": 123}},
            {"json": result},
        ],
    )
    for _ in range(3):
        with pytest.raises(RuntimeError, match="^Endpoint check failed$"):
            check_endpoint(kind, "test-id", "current-check")
        assert saved.last_request.json() == {"check_id": "current-check", "healthy": False}
    requests_mock.get(route, json={"config": {}})
    with pytest.raises(RuntimeError, match="^Endpoint check failed$"):
        check_endpoint(kind, "test-id", "current-check")
    assert saved.last_request.json() == {"check_id": "current-check", "healthy": False}
    requests_mock.get(route, json={"config": config})
    check_endpoint(kind, "test-id", "current-check")
    assert saved.last_request.json()["healthy"] is True
    if config.get("api_key"):
        assert upstream.last_request.headers["Authorization"] == "Bearer test-secret"
        assert upstream.last_request.json()["model"] == "test-model"
    requests_mock.get(route, json={"skip": True})
    check_endpoint(kind, "test-id", "old-check")
    assert upstream.call_count == 4
