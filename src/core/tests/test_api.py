import os


def test_is_alive(client):
    response = client.get("/api/isalive")
    assert {"isalive": True} == response.json


def test_is_alive_fail(client):
    response = client.get("/api/isalive")
    assert b'"isalive": false' not in response.data


def test_health_returns_service_response(client, monkeypatch):
    expected_body = {
        "healthy": False,
        "services": {"database": "down", "seed_data": "down", "broker": "n/a", "workers": "n/a"},
    }
    monkeypatch.setattr("core.api.health.health_service.get_health_response", lambda: (expected_body, 503))

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json == expected_body


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
