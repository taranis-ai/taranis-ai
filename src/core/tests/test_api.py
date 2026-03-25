import os


def test_is_alive(client):
    response = client.get("/api/isalive")
    assert {"isalive": True} == response.json


def test_is_alive_fail(client):
    response = client.get("/api/isalive")
    assert b'"isalive": false' not in response.data


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr("core.service.health.check_database", lambda: "up")
    monkeypatch.setattr("core.service.health.check_seed_data", lambda: "up")
    monkeypatch.setattr("core.service.health.broker_health_applicable", lambda: True)
    monkeypatch.setattr("core.service.health.check_broker", lambda: "up")
    monkeypatch.setattr("core.service.health.check_workers", lambda: "up")

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json == {
        "healthy": True,
        "services": {"database": "up", "seed_data": "up", "broker": "up", "workers": "up"},
    }


def test_health_database_failure_returns_503(client, monkeypatch):
    monkeypatch.setattr("core.service.health.check_database", lambda: "down")
    monkeypatch.setattr("core.service.health.broker_health_applicable", lambda: False)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json == {
        "healthy": False,
        "services": {"database": "down", "seed_data": "down", "broker": "n/a", "workers": "n/a"},
    }


def test_health_seed_data_failure_returns_503(client, monkeypatch):
    monkeypatch.setattr("core.service.health.check_database", lambda: "up")
    monkeypatch.setattr("core.service.health.check_seed_data", lambda: "down")
    monkeypatch.setattr("core.service.health.broker_health_applicable", lambda: False)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json == {
        "healthy": False,
        "services": {"database": "up", "seed_data": "down", "broker": "n/a", "workers": "n/a"},
    }


def test_auth_login(client):
    body = {"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")}
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 200


def test_access_token(access_token):
    assert access_token is not None


def test_user_profile(client, auth_header):
    response = client.get("/api/users/profile", headers=auth_header)
    assert response.json
    assert response.data
    assert response.status_code == 200


def test_auth_logout(app, client, auth_header):
    from core.model.token_blacklist import TokenBlacklist

    response = client.delete("/api/auth/logout", headers=auth_header)
    assert response.status_code == 200

    with app.app_context():
        TokenBlacklist.delete_all()
