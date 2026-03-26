import importlib
import os


def _reload_external_auth_modules():
    import core
    import core.api.auth
    import core.auth.external_authenticator
    import core.config
    import core.managers.auth_manager

    importlib.reload(core.config)
    importlib.reload(core.auth.external_authenticator)
    importlib.reload(core.managers.auth_manager)
    importlib.reload(core.api.auth)
    importlib.reload(core)


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


def test_auth_login_external_authenticator(tmp_path, monkeypatch):
    db_path = tmp_path / "external-auth.sqlite"
    env_vars = {
        "API_KEY": "test_key",
        "JWT_SECRET_KEY": "test_key_for_tests_only_do_not_use",
        "DEBUG": "true",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "QUEUE_BROKER_URL": "memory://localhost",
        "PRE_SEED_PASSWORD_USER": "test",
        "DISABLE_SSE": "True",
        "SERVER_NAME": "localhost",
        "TARANIS_CORE_SENTRY_DSN": "",
        "FLASK_RUN_PORT": "5000",
        "DISABLE_SCHEDULER": "True",
        "TARANIS_AUTHENTICATOR": "external",
        "EXTERNAL_AUTH_USER": "X-EXTERNAL-USER",
        "EXTERNAL_AUTH_ROLES": "X-EXTERNAL-ROLES",
        "EXTERNAL_AUTH_NAME": "X-EXTERNAL-NAME",
        "EXTERNAL_AUTH_ORGANIZATION": "X-EXTERNAL-ORGANIZATION",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    try:
        _reload_external_auth_modules()

        from core import create_app
        from core.model.user import User

        app = create_app()
        client = app.test_client()

        response = client.post(
            "/api/auth/login",
            headers={
                "X-EXTERNAL-USER": "external-user",
                "X-EXTERNAL-ROLES": "User",
                "X-EXTERNAL-NAME": "External User",
                "X-EXTERNAL-ORGANIZATION": "External Org",
            },
        )

        assert response.status_code == 200
        access_token = response.get_json()["access_token"]
        assert access_token

        user_response = client.get("/api/users/", headers={"Authorization": f"Bearer {access_token}"})

        assert user_response.status_code == 200
        assert user_response.get_json()["username"] == "external-user"
        assert user_response.get_json()["name"] == "External User"
        assert user_response.get_json()["organization"]["name"] == "External Org"
        assert any(role["name"] == "User" for role in user_response.get_json()["roles"])

        with app.app_context():
            user = User.find_by_name("external-user")
            assert user is not None
            assert user.name == "External User"
            assert user.organization is not None
            assert user.organization.name == "External Org"
            assert any(role.name == "User" for role in user.roles)
    finally:
        monkeypatch.undo()
        _reload_external_auth_modules()


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
