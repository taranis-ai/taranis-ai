from datetime import timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from flask import Flask, make_response, render_template_string, url_for
from flask_jwt_extended import create_access_token
from models.user import UserProfile

import frontend.auth as auth_module
import frontend.views.auth_views as auth_views_module


def test_logout_returns_error_when_core_raises(app, monkeypatch):
    mock_api = Mock()
    mock_api.logout.side_effect = Exception("core unavailable")
    monkeypatch.setattr(auth_module, "CoreApi", lambda: mock_api)

    with app.test_request_context("/logout"):
        response = auth_module.logout()

    assert isinstance(response, tuple)
    assert response[1] == 500
    assert "Logout failed" in response[0]


def test_logout_handles_non_json_error_response(app, monkeypatch):
    core_response = Mock()
    core_response.ok = False
    core_response.status_code = 502
    core_response.json.side_effect = ValueError("not json")

    mock_api = Mock()
    mock_api.logout.return_value = core_response
    monkeypatch.setattr(auth_module, "CoreApi", lambda: mock_api)

    with app.test_request_context("/logout"):
        response = auth_module.logout()

    assert isinstance(response, tuple)
    assert response[1] == 502
    assert "Logout failed" in response[0]


def test_is_safe_redirect_target_allows_relative_path(app):
    with app.test_request_context("/frontend/login"):
        assert auth_module.is_safe_redirect_target(url_for("admin.dashboard"))


def test_is_safe_redirect_target_rejects_unknown_relative_path(app):
    with app.test_request_context("/frontend/login"):
        assert not auth_module.is_safe_redirect_target("/does-not-exist")


def test_is_safe_redirect_target_rejects_login_route(app):
    with app.test_request_context("/frontend/login"):
        assert not auth_module.is_safe_redirect_target(url_for("base.login"))
        assert not auth_module.is_safe_redirect_target(f"{url_for('base.login')}/")


def test_is_safe_redirect_target_rejects_external_host(app):
    with app.test_request_context("/frontend/login"):
        assert not auth_module.is_safe_redirect_target("https://evil.example/path")


def test_is_safe_redirect_target_rejects_network_path_variants(app):
    with app.test_request_context("/frontend/login"):
        assert not auth_module.is_safe_redirect_target("//evil.example/path")
        assert not auth_module.is_safe_redirect_target("/\\evil.example/path")
        assert not auth_module.is_safe_redirect_target("/%2F%2Fevil.example/path")


@pytest.mark.parametrize(
    ("permissions", "expected"),
    [
        (["ALL"], True),
        (["ADMIN_OPERATIONS"], True),
        (["CONFIG_USERS"], True),
        (["ASSESS_ACCESS", "CONFIG_WORD_LISTS"], True),
        (["ASSESS_ACCESS", "ANALYZE_ACCESS"], False),
        ([], False),
        (None, False),
    ],
)
def test_user_has_admin_permissions(permissions, expected):
    assert auth_module.user_has_admin_permissions(permissions) is expected


def test_authenticated_request_fetches_user_info_once(app: Flask, auth_user: UserProfile, monkeypatch: pytest.MonkeyPatch) -> None:
    user_info_calls: list[str] = []

    class CoreApiStub:
        def api_get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            user_info_calls.append(endpoint)
            return auth_user.model_dump(mode="json")

    monkeypatch.setattr(auth_module, "CoreApi", CoreApiStub)

    with app.app_context():
        access_token = create_access_token(identity=auth_user)

    protected_view = auth_module.auth_required()(
        lambda: render_template_string("{{ get_locale() }} {{ get_timezone() }} {{ authenticated_user.username }}")
    )
    headers = {"Cookie": f"{auth_module.Config.JWT_ACCESS_COOKIE_NAME}={access_token}"}
    with app.test_request_context("/frontend/admin/osint-sources", headers=headers):
        response = protected_view()
        assert isinstance(response, str)
        assert "admin" in response

    assert user_info_calls == ["/users"]


def test_admin_required_redirects_when_current_user_is_missing(app, monkeypatch):
    monkeypatch.setattr(auth_module, "verify_jwt_in_request", lambda: None)
    monkeypatch.setattr(auth_module, "get_jwt_identity", lambda: "admin")
    monkeypatch.setattr(auth_module, "current_user", None)

    protected_view = auth_module.admin_required()(lambda: make_response("ok"))

    with app.test_request_context("/frontend/admin/attributes"):
        response = protected_view()

    assert response.status_code == 302
    assert "/login" in response.location


def test_expired_token_callback_redirects_to_login_and_clears_access_cookies(app, monkeypatch):
    monkeypatch.setitem(app.config, "JWT_COOKIE_CSRF_PROTECT", True)
    dashboard_path = None
    with app.app_context():
        dashboard_path = url_for("admin.dashboard")
        login_path = url_for("base.login", next=dashboard_path)

    with app.test_request_context(dashboard_path):
        response = auth_module.expired_token_callback({}, {})

    assert response.status_code == 302
    assert response.location.endswith(login_path)

    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith(f"{app.config['JWT_ACCESS_COOKIE_NAME']}=;") for header in set_cookie_headers)
    assert any(header.startswith(f"{app.config['JWT_ACCESS_CSRF_COOKIE_NAME']}=;") for header in set_cookie_headers)


def test_expired_token_callback_clears_suffixed_path_scoped_cookies(app, monkeypatch):
    from frontend.config import Settings

    settings = Settings(TARANIS_BASE_PATH="/q/", JWT_COOKIE_SUFFIX="_q")
    cookie_settings = (
        "JWT_ACCESS_COOKIE_NAME",
        "JWT_ACCESS_CSRF_COOKIE_NAME",
        "JWT_ACCESS_COOKIE_PATH",
        "JWT_ACCESS_CSRF_COOKIE_PATH",
    )
    for name in cookie_settings:
        monkeypatch.setitem(app.config, name, getattr(settings, name))
    monkeypatch.setitem(app.config, "JWT_COOKIE_CSRF_PROTECT", True)

    with app.test_request_context("/q/frontend/dashboard"):
        response = auth_module.expired_token_callback({}, {})

    set_cookie_headers = response.headers.getlist("Set-Cookie")
    for cookie_name in (
        settings.JWT_ACCESS_COOKIE_NAME,
        settings.JWT_ACCESS_CSRF_COOKIE_NAME,
    ):
        assert any(header.startswith(f"{cookie_name}=;") and "Path=/q/" in header for header in set_cookie_headers)


@pytest.mark.parametrize(
    ("minutes_until_expiry", "token_location", "expect_refresh"),
    [(10, "cookies", True), (60, "cookies", False), (10, "headers", False)],
)
def test_authenticated_requests_refresh_only_expiring_access_cookies(
    app: Flask,
    auth_user: UserProfile,
    monkeypatch: pytest.MonkeyPatch,
    minutes_until_expiry: int,
    token_location: str,
    expect_refresh: bool,
) -> None:
    monkeypatch.setitem(app.config, "JWT_COOKIE_CSRF_PROTECT", True)
    monkeypatch.setattr(auth_module, "get_user_from_cache", lambda identity: auth_user)
    core_response = Mock(ok=True)
    core_response.raw.headers.getlist.return_value = [
        f"{app.config['JWT_ACCESS_COOKIE_NAME']}=renewed; Path=/",
        f"{app.config['JWT_ACCESS_CSRF_COOKIE_NAME']}=renewed; Path=/",
    ]
    core_api = Mock()
    core_api.refresh.return_value = core_response
    monkeypatch.setattr(auth_module, "CoreApi", lambda: core_api)
    with app.app_context():
        access_token = create_access_token(identity=auth_user, expires_delta=timedelta(minutes=minutes_until_expiry))
        protected_path = url_for("base.notification")

    client = app.test_client()
    headers = {}
    if token_location == "cookies":
        client.set_cookie(key=app.config["JWT_ACCESS_COOKIE_NAME"], value=access_token)
    else:
        headers["Authorization"] = f"Bearer {access_token}"
    response = client.get(protected_path, headers=headers)

    assert response.status_code == 200
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith(f"{app.config['JWT_ACCESS_COOKIE_NAME']}=") for header in set_cookie_headers) is expect_refresh
    assert any(header.startswith(f"{app.config['JWT_ACCESS_CSRF_COOKIE_NAME']}=") for header in set_cookie_headers) is expect_refresh
    assert core_api.refresh.call_count == int(expect_refresh)


def test_revoked_access_cookie_is_cleared_instead_of_refreshed(app: Flask, auth_user: UserProfile, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(app.config, "JWT_COOKIE_CSRF_PROTECT", True)
    monkeypatch.setattr(auth_module, "get_user_from_cache", lambda identity: auth_user)
    core_response = Mock(ok=False, status_code=401)
    core_api = Mock()
    core_api.refresh.return_value = core_response
    monkeypatch.setattr(auth_module, "CoreApi", lambda: core_api)
    with app.app_context():
        access_token = create_access_token(identity=auth_user, expires_delta=timedelta(minutes=10))
        protected_path = url_for("base.notification")

    client = app.test_client()
    client.set_cookie(key=app.config["JWT_ACCESS_COOKIE_NAME"], value=access_token)
    response = client.get(protected_path)

    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith(f"{app.config['JWT_ACCESS_COOKIE_NAME']}=;") for header in set_cookie_headers)
    assert any(header.startswith(f"{app.config['JWT_ACCESS_CSRF_COOKIE_NAME']}=;") for header in set_cookie_headers)


def test_protected_route_with_expired_cookie_redirects_to_login_with_next(app, auth_user):
    with app.app_context():
        expires_delta = timedelta(seconds=-(app.config["JWT_DECODE_LEEWAY"] + 5))
        expired_token = create_access_token(identity=auth_user, expires_delta=expires_delta)
        protected_path = url_for("base.notification")
        login_path = url_for("base.login", next=protected_path)

    client = app.test_client()
    client.set_cookie(key=app.config["JWT_ACCESS_COOKIE_NAME"], value=expired_token)
    response = client.get(protected_path)

    assert response.status_code == 302
    assert response.location.endswith(login_path)


def test_login_page_renders_with_expired_cookie(app, auth_user, monkeypatch):
    mock_api = Mock()
    mock_api.get_login_data.return_value = {"auth_method": "database"}
    monkeypatch.setattr(auth_views_module, "CoreApi", lambda: mock_api)

    with app.app_context():
        expires_delta = timedelta(seconds=-(app.config["JWT_DECODE_LEEWAY"] + 5))
        expired_token = create_access_token(identity=auth_user, expires_delta=expires_delta)
        login_path = url_for("base.login")

    client = app.test_client()
    client.set_cookie(key=app.config["JWT_ACCESS_COOKIE_NAME"], value=expired_token)
    response = client.get(login_path)

    assert response.status_code == 200
    assert response.headers.get("Location") is None
