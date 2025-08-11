import os
from flask_jwt_extended import create_access_token, verify_jwt_in_request

from core.managers.auth_manager import auth_required, api_key_required


@auth_required(permissions=["ADMIN_OPERATIONS"])
def admin_endpoint():
    return {"admin": True}, 200


@api_key_required
def protected_endpoint():
    return {"ok": True}, 200


class TestAuth:
    def test_auth_required_with_permissions(self, app, admin_user, non_admin_user):
        # no token test
        with app.test_request_context(headers={}):
            response = admin_endpoint()
            assert response == ({"error": "not authorized"}, 401)

        # non-admin test
        token = create_access_token(identity=non_admin_user)
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            verify_jwt_in_request()
            response = admin_endpoint()
            assert response == ({"error": "forbidden"}, 403)

        # admin test
        token = create_access_token(identity=admin_user)
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            verify_jwt_in_request()
            response = admin_endpoint()
            assert response == ({"admin": True}, 200)

    def test_valid_api_key(self, app):
        valid_key = os.getenv("API_KEY")
        assert valid_key == "test_key"

        with app.test_request_context(headers={"Authorization": f"Bearer {valid_key}"}):
            response = protected_endpoint()
            assert response == ({"ok": True}, 200)

    def test_missing_authorization_header(self, app):
        with app.test_request_context(headers={}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)

    def test_malformed_authorization_header(self, app):
        with app.test_request_context(headers={"Authorization": "Token abc123"}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)

    def test_invalid_api_key(self, app):
        with app.test_request_context(headers={"Authorization": "Bearer wrong-key"}):
            response = protected_endpoint()
            assert response == ({"error": "not authorized"}, 401)
