from unittest.mock import Mock

import pytest
from flask import url_for

import frontend.auth as auth_module


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


def test_admin_required_redirects_when_current_user_is_missing(app, monkeypatch):
    monkeypatch.setattr(auth_module, "verify_jwt_in_request", lambda: None)
    monkeypatch.setattr(auth_module, "get_jwt_identity", lambda: "admin")
    monkeypatch.setattr(auth_module, "current_user", None)

    protected_view = auth_module.admin_required()(lambda: "ok")

    with app.test_request_context("/frontend/admin/attributes"):
        response = protected_view()

    assert response.status_code == 302
    assert "/login" in response.location
