import uuid
from unittest.mock import Mock

import pytest
import requests
from pydantic import SecretStr

from core.config import Config
from core.managers.realtime_publisher import RealtimePublisher


def _publisher(response_payload=None, side_effect=None):
    session = Mock(spec=requests.Session)
    response = Mock(spec=requests.Response)
    response.json.return_value = {"result": {"responses": [{}]}} if response_payload is None else response_payload
    response.raise_for_status.return_value = None
    session.post.return_value = response
    session.post.side_effect = side_effect
    return RealtimePublisher(session), session


@pytest.fixture
def enabled_realtime(monkeypatch):
    monkeypatch.setattr(Config, "REALTIME_ENABLED", True)
    monkeypatch.setattr(Config, "CENTRIFUGO_API_URL", "http://centrifugo:9000")
    monkeypatch.setattr(Config, "CENTRIFUGO_API_KEY", SecretStr("dedicated-realtime-key"))


def test_disabled_publisher_performs_no_network_io(monkeypatch):
    monkeypatch.setattr(Config, "REALTIME_ENABLED", False)
    publisher, session = _publisher()

    assert publisher.assess_changed() is False
    session.post.assert_not_called()


def test_publish_uses_explicit_channel_dedicated_key_and_strict_timeout(enabled_realtime):
    publisher, session = _publisher()
    organization_id = str(uuid.uuid7())
    report_item_id = str(uuid.uuid7())

    assert publisher.report_item_changed(report_item_id, organization_id, "created") is True

    request = session.post.call_args
    assert request.args == ("http://centrifugo:9000/api/broadcast",)
    assert request.kwargs["headers"]["X-API-Key"] == "dedicated-realtime-key"
    assert request.kwargs["timeout"] == (0.2, 0.3)
    assert request.kwargs["json"]["channels"] == [f"org:{organization_id}"]
    event = request.kwargs["json"]["data"]
    assert event["v"] == 1
    assert uuid.UUID(event["id"]).version == 7
    assert event["type"] == "report.item.changed"
    assert event["resource"] == {"kind": "report_item", "id": report_item_id}


@pytest.mark.parametrize(
    "response_payload",
    [
        {},
        {"error": {"code": 100, "message": "rejected"}},
        {"result": {}},
        {"result": {"responses": [{"error": {"code": 100, "message": "rejected"}}]}},
    ],
)
def test_api_level_failures_do_not_escape(enabled_realtime, response_payload):
    publisher, _ = _publisher(response_payload=response_payload)

    assert publisher.assess_changed() is False


def test_timeout_does_not_escape_or_disable_later_attempts(enabled_realtime):
    publisher, session = _publisher(side_effect=requests.ReadTimeout())

    assert publisher.assess_changed() is False

    session.post.side_effect = None
    assert publisher.assess_changed() is True
    assert session.post.call_count == 2


def test_unexpected_realtime_failure_does_not_escape(enabled_realtime):
    publisher, _ = _publisher(side_effect=RuntimeError("isolated realtime failure"))

    assert publisher.assess_changed() is False


def test_product_event_uses_user_limited_channel(enabled_realtime):
    publisher, session = _publisher()
    product_id = str(uuid.uuid7())
    user_id = str(uuid.uuid7())

    assert publisher.product_rendered(product_id, user_id, "success") is True
    assert session.post.call_args.kwargs["json"]["channels"] == [f"user:#{user_id}"]


def test_osint_source_preview_event_uses_user_limited_channel(enabled_realtime):
    publisher, session = _publisher()
    source_id = str(uuid.uuid7())
    user_id = str(uuid.uuid7())

    assert publisher.osint_source_preview_finished(source_id, user_id, "PREVIEW") is True

    request_json = session.post.call_args.kwargs["json"]
    assert request_json["channels"] == [f"user:#{user_id}"]
    assert request_json["data"]["type"] == "osint_source.preview.finished"
    assert request_json["data"]["resource"] == {"kind": "osint_source", "id": source_id}
    assert request_json["data"]["data"] == {"status": "PREVIEW"}


def test_broadcast_notification_preserves_message_and_is_persistent(enabled_realtime):
    publisher, session = _publisher()

    assert publisher.broadcast_notification("  Maintenance at 18:00  ") is True

    request_json = session.post.call_args.kwargs["json"]
    assert request_json["channels"] == ["global:events"]
    assert request_json["data"]["type"] == "notification.broadcast"
    assert request_json["data"]["data"] == {
        "message": "  Maintenance at 18:00  ",
        "persistent": True,
    }


def test_connected_clients_reads_global_channel_presence(enabled_realtime):
    publisher, session = _publisher(
        response_payload={
            "result": {
                "presence": {
                    "client-2": {"client": "client-2", "user": "user-2"},
                    "client-1": {"client": "client-1", "user": "user-1"},
                }
            }
        }
    )

    assert publisher.connected_clients() == [
        {"client_id": "client-1", "user_id": "user-1"},
        {"client_id": "client-2", "user_id": "user-2"},
    ]
    request = session.post.call_args
    assert request.args == ("http://centrifugo:9000/api/presence",)
    assert request.kwargs["json"] == {"channel": "global:events"}
    assert request.kwargs["timeout"] == (0.2, 0.3)


def test_connected_clients_returns_none_for_invalid_presence(enabled_realtime):
    publisher, _ = _publisher(response_payload={"error": {"code": 108, "message": "not available"}})

    assert publisher.connected_clients() is None
