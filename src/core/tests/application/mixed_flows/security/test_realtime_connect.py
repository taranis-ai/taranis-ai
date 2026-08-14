import time
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from core.config import Config
from core.managers.realtime_publisher import realtime_publisher


PROXY_SECRET = "dedicated-connect-proxy-secret"


def _headers(secret=PROXY_SECRET):
    return {"X-Realtime-Proxy-Key": secret}


def _configure_realtime(monkeypatch):
    monkeypatch.setattr(Config, "REALTIME_ENABLED", True)
    monkeypatch.setattr(Config, "CENTRIFUGO_CONNECT_PROXY_SECRET", SecretStr(PROXY_SECRET))


def test_connect_proxy_authenticates_access_cookie_and_scopes_channels(app, access_token, admin_user, monkeypatch):
    _configure_realtime(monkeypatch)
    client = app.test_client()
    client.set_cookie(Config.JWT_ACCESS_COOKIE_NAME, access_token)

    response = client.post("/api/realtime/connect", headers=_headers(), json={})

    assert response.status_code == 200
    result = response.get_json()["result"]
    assert result["user"] == admin_user.id
    assert result["channels"] == [
        "global:events",
        f"org:{admin_user.organization_id}",
        f"user:#{admin_user.id}",
    ]
    assert int(time.time()) < result["expire_at"] <= int(time.time()) + 900


def test_connect_proxy_rejects_wrong_proxy_secret_before_authentication(app, monkeypatch):
    _configure_realtime(monkeypatch)

    response = app.test_client().post(
        "/api/realtime/connect",
        headers=_headers(secret="wrong-secret"),
        json={},
    )

    assert response.status_code == 403


def test_connect_proxy_authenticates_without_an_origin_header(app, monkeypatch):
    _configure_realtime(monkeypatch)

    response = app.test_client().post("/api/realtime/connect", headers=_headers(), json={})

    assert response.status_code == 200


def test_connect_proxy_returns_terminal_disconnect_without_valid_cookie(app, monkeypatch):
    _configure_realtime(monkeypatch)

    response = app.test_client().post("/api/realtime/connect", headers=_headers(), json={})

    assert response.status_code == 200
    assert response.get_json() == {"disconnect": {"code": 4501, "reason": "unauthorized"}}


def test_connect_proxy_disconnects_when_realtime_is_disabled(app, monkeypatch):
    _configure_realtime(monkeypatch)
    monkeypatch.setattr(Config, "REALTIME_ENABLED", False)

    response = app.test_client().post("/api/realtime/connect", headers=_headers(), json={})

    assert response.status_code == 200
    assert response.get_json() == {"disconnect": {"code": 4501, "reason": "unauthorized"}}


def test_admin_can_broadcast_exact_notification_text(client, auth_header, monkeypatch):
    publish = Mock(return_value=True)
    monkeypatch.setattr(realtime_publisher, "broadcast_notification", publish)

    response = client.post(
        "/api/realtime/broadcast",
        headers=auth_header,
        json={"message": "  Maintenance at 18:00  "},
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "Broadcast sent"}
    publish.assert_called_once_with("  Maintenance at 18:00  ")


def test_non_admin_cannot_broadcast(client, auth_header_user_permissions, monkeypatch):
    publish = Mock(return_value=True)
    monkeypatch.setattr(realtime_publisher, "broadcast_notification", publish)

    response = client.post(
        "/api/realtime/broadcast",
        headers=auth_header_user_permissions,
        json={"message": "Maintenance"},
    )

    assert response.status_code == 403
    publish.assert_not_called()


@pytest.mark.parametrize("message", [None, "", "   ", "x" * 501])
def test_broadcast_rejects_invalid_messages(client, auth_header, monkeypatch, message):
    publish = Mock(return_value=True)
    monkeypatch.setattr(realtime_publisher, "broadcast_notification", publish)

    response = client.post(
        "/api/realtime/broadcast",
        headers=auth_header,
        json={"message": message},
    )

    assert response.status_code == 400
    publish.assert_not_called()


def test_broadcast_reports_realtime_failure(client, auth_header, monkeypatch):
    monkeypatch.setattr(realtime_publisher, "broadcast_notification", Mock(return_value=False))

    response = client.post(
        "/api/realtime/broadcast",
        headers=auth_header,
        json={"message": "Maintenance"},
    )

    assert response.status_code == 503
    assert response.get_json() == {"error": "Broadcast could not be sent"}


def test_admin_can_list_connected_clients(client, auth_header, admin_user, monkeypatch):
    monkeypatch.setattr(
        realtime_publisher,
        "connected_clients",
        Mock(
            return_value=[
                {"client_id": "client-1", "user_id": admin_user.id},
                {"client_id": "client-2", "user_id": admin_user.id},
            ]
        ),
    )

    response = client.get("/api/realtime/clients", headers=auth_header)

    assert response.status_code == 200
    assert response.get_json() == {
        "num_clients": 2,
        "num_users": 1,
        "clients": [
            {"client_id": "client-1", "user_id": admin_user.id, "username": admin_user.username},
            {"client_id": "client-2", "user_id": admin_user.id, "username": admin_user.username},
        ],
    }


def test_non_admin_cannot_list_connected_clients(client, auth_header_user_permissions, monkeypatch):
    presence = Mock(return_value=[])
    monkeypatch.setattr(realtime_publisher, "connected_clients", presence)

    response = client.get("/api/realtime/clients", headers=auth_header_user_permissions)

    assert response.status_code == 403
    presence.assert_not_called()


def test_connected_clients_reports_presence_failure(client, auth_header, monkeypatch):
    monkeypatch.setattr(realtime_publisher, "connected_clients", Mock(return_value=None))

    response = client.get("/api/realtime/clients", headers=auth_header)

    assert response.status_code == 503
    assert response.get_json() == {"error": "Connected clients are unavailable"}
