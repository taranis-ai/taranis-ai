import importlib
import os
from copy import deepcopy


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


def test_auth_login(client):
    body = {"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")}
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 200


def test_auth_refresh_is_header_only_and_rejects_revoked_tokens(client, app, monkeypatch):
    from core.auth import base_authenticator
    from core.model.user import User

    login_response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")},
    )
    access_token = login_response.json["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        last_login = user.last_login
    login_activities = []
    monkeypatch.setattr(base_authenticator.logger, "store_user_activity", lambda *args: login_activities.append(args))

    assert client.get("/api/auth/refresh").status_code == 401

    refresh_response = client.get("/api/auth/refresh", headers=headers)
    assert refresh_response.status_code == 200
    assert refresh_response.json["access_token"] != access_token
    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        assert user.last_login == last_login
    assert login_activities == []

    assert client.delete("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/refresh", headers=headers).status_code == 401


def test_auth_login_sets_suffixed_path_scoped_cookies(client, app, monkeypatch):
    from core.config import Settings

    settings = Settings(APPLICATION_ROOT="/q/", JWT_COOKIE_SUFFIX="_q")
    cookie_settings = (
        "JWT_ACCESS_COOKIE_NAME",
        "JWT_ACCESS_CSRF_COOKIE_NAME",
        "JWT_ACCESS_COOKIE_PATH",
        "JWT_ACCESS_CSRF_COOKIE_PATH",
    )
    for name in cookie_settings:
        monkeypatch.setitem(app.config, name, getattr(settings, name))

    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")},
    )

    assert response.status_code == 200
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    for cookie_name in (
        settings.JWT_ACCESS_COOKIE_NAME,
        settings.JWT_ACCESS_CSRF_COOKIE_NAME,
    ):
        assert any(header.startswith(f"{cookie_name}=") and "Path=/q/" in header for header in set_cookie_headers)


def test_auth_login_updates_last_login(client, app, monkeypatch):
    from core.auth import base_authenticator
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        previous_last_login = user.last_login
    login_activities = []
    monkeypatch.setattr(base_authenticator.logger, "store_user_activity", lambda *args: login_activities.append(args))

    body = {"username": "user", "password": os.getenv("PRE_SEED_PASSWORD_USER")}
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 200

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        assert user.last_login is not None
        if previous_last_login is not None:
            assert user.last_login >= previous_last_login
    assert len(login_activities) == 1
    assert login_activities[0][1:] == ("LOGIN", "Successful")


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
            assert user.last_login is not None
            assert user.organization is not None
            assert user.organization.name == "External Org"
            assert any(role.name == "User" for role in user.roles)
    finally:
        monkeypatch.undo()
        _reload_external_auth_modules()


def test_access_token(access_token):
    assert access_token is not None


def test_user_profile(app, client, auth_header):
    from core.managers.db_manager import db
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("admin")
        assert user is not None
        original_profile = deepcopy(user.profile)
        saved_filters = [{"id": "filter-1", "name": "Important", "filters": {"important": "true"}, "is_default": True}]
        user.profile = {**(user.profile or {}), "assess_default_filters": {"read": "true"}, "assess_saved_filters": saved_filters}
        db.session.commit()

    try:
        response = client.get("/api/users/profile", headers=auth_header)

        assert response.json
        assert response.data
        assert response.status_code == 200
        assert "assess_default_filters" not in response.json
        assert response.json["assess_saved_filters"] == saved_filters
    finally:
        with app.app_context():
            user = User.find_by_name("admin")
            assert user is not None
            user.profile = original_profile
            db.session.commit()


def _onboarding_task_ids(payload: dict, scope: str | None = None) -> set[str]:
    return {task["id"] for task in payload.get("pending_onboarding_tasks", []) if scope is None or task.get("scope") == scope}


def test_user_info_includes_pending_global_onboarding_for_admin(client, auth_header):
    from models.user import ADMIN_ADVANCED_TOUR_ID, ADMIN_WELCOME_TOUR_ID, USER_PRODUCT_OVERVIEW_TASK_ID

    response = client.get("/api/users/", headers=auth_header)

    assert response.status_code == 200
    payload = response.get_json()
    assert {ADMIN_WELCOME_TOUR_ID, ADMIN_ADVANCED_TOUR_ID}.issubset(_onboarding_task_ids(payload, "global"))
    assert USER_PRODUCT_OVERVIEW_TASK_ID in _onboarding_task_ids(payload, "user")


def test_user_info_excludes_global_onboarding_for_non_admin(client, auth_header_user_permissions):
    from models.user import ADMIN_ADVANCED_TOUR_ID, ADMIN_WELCOME_TOUR_ID, USER_PRODUCT_OVERVIEW_TASK_ID

    response = client.get("/api/users/", headers=auth_header_user_permissions)

    assert response.status_code == 200
    payload = response.get_json()
    assert ADMIN_WELCOME_TOUR_ID not in _onboarding_task_ids(payload, "global")
    assert ADMIN_ADVANCED_TOUR_ID not in _onboarding_task_ids(payload, "global")
    assert USER_PRODUCT_OVERVIEW_TASK_ID in _onboarding_task_ids(payload, "user")


def test_user_info_excludes_finished_user_onboarding_task(app, client, auth_header_user_permissions):
    from models.user import USER_PRODUCT_OVERVIEW_TASK_ID

    from core.managers.db_manager import db
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None
        original_profile = deepcopy(user.profile)

    try:
        update_response = client.post(
            "/api/users/profile",
            json={"onboarding_tasks": {USER_PRODUCT_OVERVIEW_TASK_ID: "dismissed"}},
            headers=auth_header_user_permissions,
        )
        assert update_response.status_code == 200

        response = client.get("/api/users/", headers=auth_header_user_permissions)

        assert response.status_code == 200
        assert USER_PRODUCT_OVERVIEW_TASK_ID not in _onboarding_task_ids(response.get_json(), "user")
    finally:
        with app.app_context():
            user = User.find_by_name("user")
            assert user is not None
            user.profile = original_profile
            db.session.commit()


def test_user_info_excludes_finished_admin_onboarding_task(app, client, auth_header):
    from models.user import ADMIN_ADVANCED_TOUR_ID, ADMIN_WELCOME_TOUR_ID

    from core.managers.db_manager import db
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("admin")
        assert user is not None
        original_profile = deepcopy(user.profile)

    try:
        update_response = client.post(
            "/api/users/profile",
            json={"onboarding_tasks": {ADMIN_WELCOME_TOUR_ID: "dismissed"}},
            headers=auth_header,
        )
        assert update_response.status_code == 200

        response = client.get("/api/users/", headers=auth_header)

        assert response.status_code == 200
        payload = response.get_json()
        assert ADMIN_WELCOME_TOUR_ID not in _onboarding_task_ids(payload, "global")
        assert ADMIN_ADVANCED_TOUR_ID in _onboarding_task_ids(payload, "global")
    finally:
        with app.app_context():
            user = User.find_by_name("admin")
            assert user is not None
            user.profile = original_profile
            db.session.commit()


def test_auth_logout(app, client, auth_header):
    from core.model.token_blacklist import TokenBlacklist

    response = client.delete("/api/auth/logout", headers=auth_header)
    assert response.status_code == 200

    with app.app_context():
        TokenBlacklist.delete_all()
