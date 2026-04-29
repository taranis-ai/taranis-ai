import os

from core.managers import auth_manager
from core.managers.auth_manager import api_key_or_auth_required, api_key_required, auth_required


@auth_required(permissions=["ADMIN_OPERATIONS"])
def admin_endpoint():
    return {"admin": True}, 200


@api_key_required
def protected_endpoint():
    return {"ok": True}, 200


@api_key_or_auth_required(permissions=["ADMIN_OPERATIONS"])
def protected_or_jwt_endpoint():
    return {"ok": True}, 200


class TestAuth:
    def test_auth_required(self, app, access_token, access_token_user_permissions, access_token_no_permissions):
        # no token test
        with app.test_request_context(headers={}):
            response = admin_endpoint()
            assert response == ({"error": "not authorized"}, 401)

        # non-admin test
        with app.test_request_context(headers={"Authorization": f"Bearer {access_token_user_permissions}"}):
            response = admin_endpoint()
            assert response == ({"error": "forbidden"}, 403)

        # admin test
        with app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
            response = admin_endpoint()
            assert response == ({"admin": True}, 200)

        # fake user with no permissions
        with app.test_request_context(headers={"Authorization": f"Bearer {access_token_no_permissions}"}):
            response = admin_endpoint()
            assert response == ({"error": "not authorized"}, 401)

    def test_api_key_required(self, app):
        valid_key = os.getenv("API_KEY")
        assert valid_key == "test_key"

        # test with valid API key
        with app.test_request_context(headers={"Authorization": f"Bearer {valid_key}"}):
            response = protected_endpoint()
            assert response == ({"ok": True}, 200)

        # missing authorization header
        with app.test_request_context(headers={}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)

        # malformed authorization header
        with app.test_request_context(headers={"Authorization": "Token abc123"}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)

        # invalid API key
        with app.test_request_context(headers={"Authorization": "Bearer wrong-key"}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)

    def test_api_key_or_auth_required_logs_api_key_error_before_valid_jwt(self, app, access_token, monkeypatch):
        auth_error_messages: list[str] = []
        info_messages: list[str] = []

        monkeypatch.setattr(auth_manager.logger, "store_auth_error_activity", auth_error_messages.append)
        monkeypatch.setattr(auth_manager.logger, "info", info_messages.append)

        with app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
            response = protected_or_jwt_endpoint()

        assert response == ({"ok": True}, 200)
        assert auth_error_messages == ["Incorrect api key"]
        assert info_messages == ["Authenticated with JWT after failed API key attempt"]

    def test_api_key_or_auth_required_logs_api_key_error_twice_for_invalid_jwt(self, app, monkeypatch):
        logged_messages: list[str] = []

        monkeypatch.setattr(auth_manager.logger, "store_auth_error_activity", logged_messages.append)

        with app.test_request_context(headers={"Authorization": "Bearer not-a-jwt"}):
            response = protected_or_jwt_endpoint()

        assert response == ({"error": "not authorized"}, 401)
        assert logged_messages == ["Incorrect api key", "Incorrect api key"]
