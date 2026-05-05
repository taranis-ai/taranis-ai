import os


def test_is_alive(client):
    response = client.get("/api/isalive")
    assert {"isalive": True} == response.json


def test_is_alive_fail(client):
    response = client.get("/api/isalive")
    assert b'"isalive": false' not in response.data


def test_auth_login(client):
    body = {"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")}
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 200


def test_auth_login_updates_last_login(client, app):
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        previous_last_login = user.last_login

    body = {"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")}
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 200

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        assert user.last_login is not None
        if previous_last_login is not None:
            assert user.last_login >= previous_last_login


def test_auth_login_external_authenticator(app, client):
    from core.auth.database_authenticator import DatabaseAuthenticator
    from core.auth.external_authenticator import ExternalAuthenticator
    from core.config import Config
    from core.managers import auth_manager
    from core.model.user import User

    original_authenticator = Config.TARANIS_AUTHENTICATOR
    original_current_authenticator = auth_manager.current_authenticator
    original_headers = (
        Config.EXTERNAL_AUTH_USER,
        Config.EXTERNAL_AUTH_ROLES,
        Config.EXTERNAL_AUTH_NAME,
        Config.EXTERNAL_AUTH_ORGANIZATION,
    )

    try:
        Config.TARANIS_AUTHENTICATOR = "external"
        Config.EXTERNAL_AUTH_USER = "X-EXTERNAL-USER"
        Config.EXTERNAL_AUTH_ROLES = "X-EXTERNAL-ROLES"
        Config.EXTERNAL_AUTH_NAME = "X-EXTERNAL-NAME"
        Config.EXTERNAL_AUTH_ORGANIZATION = "X-EXTERNAL-ORGANIZATION"
        app.config.update(
            {
                "TARANIS_AUTHENTICATOR": Config.TARANIS_AUTHENTICATOR,
                "EXTERNAL_AUTH_USER": Config.EXTERNAL_AUTH_USER,
                "EXTERNAL_AUTH_ROLES": Config.EXTERNAL_AUTH_ROLES,
                "EXTERNAL_AUTH_NAME": Config.EXTERNAL_AUTH_NAME,
                "EXTERNAL_AUTH_ORGANIZATION": Config.EXTERNAL_AUTH_ORGANIZATION,
            }
        )
        auth_manager.current_authenticator = ExternalAuthenticator()

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
            assert user.last_login is not None
            assert user.organization is not None
            assert user.organization.name == "External Org"
            assert any(role.name == "User" for role in user.roles)
    finally:
        Config.TARANIS_AUTHENTICATOR = original_authenticator
        (
            Config.EXTERNAL_AUTH_USER,
            Config.EXTERNAL_AUTH_ROLES,
            Config.EXTERNAL_AUTH_NAME,
            Config.EXTERNAL_AUTH_ORGANIZATION,
        ) = original_headers
        app.config.update(
            {
                "TARANIS_AUTHENTICATOR": Config.TARANIS_AUTHENTICATOR,
                "EXTERNAL_AUTH_USER": Config.EXTERNAL_AUTH_USER,
                "EXTERNAL_AUTH_ROLES": Config.EXTERNAL_AUTH_ROLES,
                "EXTERNAL_AUTH_NAME": Config.EXTERNAL_AUTH_NAME,
                "EXTERNAL_AUTH_ORGANIZATION": Config.EXTERNAL_AUTH_ORGANIZATION,
            }
        )
        auth_manager.current_authenticator = (
            original_current_authenticator if original_authenticator != "database" else DatabaseAuthenticator()
        )


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
