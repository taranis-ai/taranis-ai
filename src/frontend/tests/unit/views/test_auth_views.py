from unittest.mock import Mock, patch

from flask import Response, url_for

import frontend.views.auth_views as auth_views_module
from frontend.views.auth_views import AuthView


def test_external_login_with_retries_handles_exception_then_succeeds(app, monkeypatch):
    mock_api = Mock()
    successful_core_response = object()
    mock_api.external_login.side_effect = [Exception("core unavailable"), None, successful_core_response]
    monkeypatch.setattr(auth_views_module, "CoreApi", lambda: mock_api)

    view = AuthView()
    with app.test_request_context("/login"):
        with patch.object(view, "login_flow", return_value=Response(status=302)) as login_flow:
            response = view._external_login_with_retries({"X-USER": "demo"}, attempts=3)

    assert response.status_code == 302
    assert mock_api.external_login.call_count == 3
    login_flow.assert_called_once_with(successful_core_response)


def test_external_login_with_retries_retries_non_redirect_response(app, monkeypatch):
    mock_api = Mock()
    mock_api.external_login.side_effect = [object(), object()]
    monkeypatch.setattr(auth_views_module, "CoreApi", lambda: mock_api)

    view = AuthView()
    with app.test_request_context("/login"):
        with patch.object(view, "login_flow", side_effect=[Response(status=401), Response(status=302)]) as login_flow:
            response = view._external_login_with_retries({"X-USER": "demo"}, attempts=2)

    assert response.status_code == 302
    assert mock_api.external_login.call_count == 2
    assert login_flow.call_count == 2


def test_external_login_with_retries_handles_falsy_response_object(app, monkeypatch):
    core_response = Mock()
    core_response.__bool__ = Mock(return_value=False)

    mock_api = Mock()
    mock_api.external_login.return_value = core_response
    monkeypatch.setattr(auth_views_module, "CoreApi", lambda: mock_api)

    view = AuthView()
    with app.test_request_context("/login"):
        with patch.object(view, "login_flow", return_value=Response(status=401)) as login_flow:
            response = view._external_login_with_retries({"X-USER": "demo"}, attempts=1)

    assert response.status_code == 401
    login_flow.assert_called_once_with(core_response)


def test_login_flow_handles_non_json_error_response(app):
    core_response = Mock()
    core_response.ok = False
    core_response.status_code = 401
    core_response.json.side_effect = ValueError("not json")

    view = AuthView()
    with app.test_request_context("/login"):
        response = view.login_flow(core_response)

    assert response.status_code == 401
    assert "Login failed" in response.get_data(as_text=True)


def test_login_flow_rejects_external_next_redirect(app):
    core_response = Mock()
    core_response.ok = True
    core_response.raw.headers.getlist.return_value = []

    view = AuthView()
    with app.test_request_context("/login?next=https://evil.example/path"):
        response = view.login_flow(core_response)

    assert response.status_code == 302
    assert response.headers["Location"] == url_for("base.dashboard")


def test_login_flow_allows_relative_next_redirect(app):
    core_response = Mock()
    core_response.ok = True
    core_response.raw.headers.getlist.return_value = []

    view = AuthView()
    with app.test_request_context("/login?next=/admin"):
        response = view.login_flow(core_response)

    assert response.status_code == 302
    assert response.headers["Location"] == "/admin"
