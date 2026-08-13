import time

from pydantic import SecretStr

from core.config import Config


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
