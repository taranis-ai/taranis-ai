from unittest.mock import Mock

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
