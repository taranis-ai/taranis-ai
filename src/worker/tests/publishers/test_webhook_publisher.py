import json
import logging
from base64 import b64encode

import pytest
from models.product import WorkerProduct

from worker.publishers import publisher_tasks
from worker.publishers.network import PublisherNetworkTimeout


@pytest.mark.parametrize("raw", [False, True], ids=["json", "raw"])
def test_webhook_delivers_render(raw, webhook_receiver, recording_core_api_factory, monkeypatch, caplog):
    url, received = webhook_receiver
    caplog.set_level(logging.DEBUG)
    content = b"%PDF-\xff\x00"
    encoded = b64encode(content)
    parameters = {"WEBHOOK_URL": f"{url}%2Freport?key=private-a%2Bb"}
    if raw:
        parameters.update(PAYLOAD_FORMAT="raw", BEARER_TOKEN="private-bearer")
    core = recording_core_api_factory(
        publisher={"type": "webhook_publisher", "parameters": parameters},
        rendered_product=WorkerProduct(data=encoded, mime_type="application/pdf"),
    )
    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core)
    assert publisher_tasks.publisher_task("prod-123", "webhook") == {"message": "Webhook delivery accepted"}
    [(method, path, auth, mime_type, body)] = received
    assert (method, path) == ("POST", "/private-route%2Freport?key=private-a%2Bb")
    if raw:
        assert (auth, mime_type, body) == ("Bearer private-bearer", "application/pdf", content)
    else:
        assert auth is None
        assert mime_type == "application/json"
        assert json.loads(body) == {
            "product_id": "prod-123",
            "title": "Example Product",
            "mime_type": "application/pdf",
            "data": encoded.decode(),
        }
    assert "private-" not in caplog.text
    assert "private-" not in str(core.put_calls)


@pytest.mark.parametrize(
    ("path", "error", "reason", "http_status"),
    [
        ("redirect", RuntimeError, "publisher_failed", 307),
        ("reject", RuntimeError, "publisher_failed", 403),
        ("untrusted-cert", RuntimeError, "publisher_failed", None),
        ("stall", PublisherNetworkTimeout, "publisher_network_timeout", None),
    ],
)
def test_webhook_failure_records_safe_result(
    path, error, reason, http_status, webhook_receiver, recording_core_api_factory, monkeypatch, caplog
):
    url, received = webhook_receiver
    if path == "untrusted-cert":
        monkeypatch.delenv("REQUESTS_CA_BUNDLE")
    parameters = {"WEBHOOK_URL": f"{url}/{path}", "BEARER_TOKEN": "private-bearer", "NETWORK_TIMEOUT": 1}
    core = recording_core_api_factory(
        publisher={"type": "webhook_publisher", "parameters": parameters},
        rendered_product=WorkerProduct(data=b"YWJj"),
    )
    monkeypatch.setattr(publisher_tasks, "CoreApi", lambda: core)
    with pytest.raises(error) as exc:
        publisher_tasks.publisher_task("prod-123", "webhook")
    assert len(received) == (0 if path == "untrusted-cert" else 1)
    submission = core.put_calls[-1]["json"]
    assert submission["status"] == "FAILURE"
    assert submission["result"].reason == reason
    data = submission["result"].data
    if http_status is None:
        assert "http_status" not in data
    else:
        assert data["http_status"] == http_status
    assert "private-" not in str(exc.value) + str(submission) + caplog.text
