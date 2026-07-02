import json

import pytest


@pytest.fixture
def audit_events(monkeypatch):
    import core.audit as audit
    from core.config import Config

    events = []
    monkeypatch.setattr(Config, "AUDIT_LOG_ENABLED", True)
    monkeypatch.setattr(audit, "write_event", events.append)
    return events


def test_write_event_outputs_json_line(capsys):
    from core.audit import write_event

    capsys.readouterr()
    write_event({"event": "audit", "path": "/api/test"})

    output = capsys.readouterr().out
    assert output.endswith("\n")
    assert json.loads(output) == {"event": "audit", "path": "/api/test"}


def test_authenticated_non_get_emits_audit_event(client, auth_header, audit_events):
    response = client.put("/api/users/profile", headers=auth_header, json={"timezone": "UTC"})

    assert response.status_code == 200
    assert len(audit_events) == 1
    event = audit_events[0]
    assert event["event"] == "audit"
    assert event["method"] == "PUT"
    assert event["path"] == "/api/users/profile"
    assert event["endpoint"] == "user.user_profile"
    assert event["status"] == 200
    assert event["username"] == "admin"
    assert event["user_id"]
    assert event["route_ids"] == {}


def test_authenticated_get_emits_no_audit_event(client, auth_header, audit_events):
    response = client.get("/api/users/profile", headers=auth_header)

    assert response.status_code == 200
    assert audit_events == []


def test_api_key_route_emits_no_audit_event(client, api_header, audit_events):
    response = client.post("/api/tasks", headers=api_header, json={})

    assert response.status_code == 400
    assert audit_events == []


def test_failed_login_audits_username_without_password(client, monkeypatch, audit_events):
    from core.auth import database_authenticator

    auth_errors: list[str] = []
    monkeypatch.setattr(database_authenticator.logger, "store_auth_error_activity", auth_errors.append)

    response = client.post("/api/auth/login", json={"username": "user", "password": "bad-password"})

    assert response.status_code == 401
    assert len(audit_events) == 1
    assert audit_events[0]["endpoint"] == "auth.login"
    assert audit_events[0]["status"] == 401
    assert audit_events[0]["username"] == "user"
    assert audit_events[0]["user_id"] is None
    assert "bad-password" not in json.dumps(audit_events[0])
    assert auth_errors == ["Authentication failed for username: user"]


def test_disabled_audit_emits_no_event(client, auth_header, monkeypatch, audit_events):
    from core.config import Config

    monkeypatch.setattr(Config, "AUDIT_LOG_ENABLED", False)

    response = client.put("/api/users/profile", headers=auth_header, json={"timezone": "UTC"})

    assert response.status_code == 200
    assert audit_events == []


def test_audit_failure_does_not_change_response(client, auth_header, monkeypatch):
    import core.audit as audit
    from core.config import Config

    monkeypatch.setattr(Config, "AUDIT_LOG_ENABLED", True)

    def fail_write_event(_event):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(audit, "write_event", fail_write_event)

    response = client.put("/api/users/profile", headers=auth_header, json={"timezone": "UTC"})

    assert response.status_code == 200
