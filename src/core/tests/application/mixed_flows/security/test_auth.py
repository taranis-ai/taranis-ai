import os

from core.auth.database_authenticator import DatabaseAuthenticator
from core.log import logger as core_logger
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

    def test_api_key_or_auth_required_logs_api_key_error_once_for_invalid_jwt(self, app, monkeypatch):
        logged_messages: list[str] = []

        monkeypatch.setattr(auth_manager.logger, "store_auth_error_activity", logged_messages.append)

        with app.test_request_context(headers={"Authorization": "Bearer not-a-jwt"}):
            response = protected_or_jwt_endpoint()

        assert response == ({"error": "not authorized"}, 401)
        assert logged_messages == ["Incorrect api key"]

    def test_database_auth_failure_logs_username_without_password(self, app, monkeypatch):
        logged_messages: list[str] = []

        monkeypatch.setattr("core.auth.database_authenticator.logger.store_auth_error_activity", logged_messages.append)

        with app.test_request_context("/api/auth/login", method="POST", json={"username": "admin", "password": "wrong"}):
            response = DatabaseAuthenticator().authenticate({"username": "admin", "password": "wrong"})

        assert response.status_code == 401
        assert logged_messages == ["Authentication failed for username: admin"]

    def test_auth_error_activity_redacts_json_password(self, app, monkeypatch):
        log_records: list[dict[str, str]] = []

        monkeypatch.setattr("core.log.Config.DEBUG", False)
        monkeypatch.setattr(core_logger, "rollback_and_store_to_db", lambda log_data: None)
        monkeypatch.setattr(core_logger.logger, "error", lambda _message, log_data: log_records.append(log_data))

        with app.test_request_context(
            "/api/auth/login",
            method="POST",
            json={"username": "admin", "password": "wrong", "profile": {"token": "abc"}, "items": [{"api_key": "key"}]},
        ):
            core_logger.store_auth_error_activity("Authentication failed for username: admin")

        assert log_records[0]["activity_detail"] == "Authentication failed for username: admin"
        assert log_records[0]["activity_data"] == (
            '{"items":[{"api_key":"***"}],"password":"***","profile":{"token":"***"},"username":"admin"}'
        )

    def test_auth_error_activity_keeps_json_password_in_debug(self, app, monkeypatch):
        log_records: list[dict[str, str]] = []

        monkeypatch.setattr("core.log.Config.DEBUG", True)
        monkeypatch.setattr(core_logger, "rollback_and_store_to_db", lambda log_data: None)
        monkeypatch.setattr(core_logger.logger, "error", lambda _message, log_data: log_records.append(log_data))

        with app.test_request_context(
            "/api/auth/login",
            method="POST",
            json={"username": "admin", "password": "debug-value", "profile": {"token": "debug-token"}},
        ):
            core_logger.store_auth_error_activity("Authentication failed for username: admin")

        assert log_records[0]["activity_data"] == ('{"password":"debug-value","profile":{"token":"debug-token"},"username":"admin"}')
