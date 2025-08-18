import os
from core.managers.auth_manager import auth_required, api_key_required


@auth_required(permissions=["ADMIN_OPERATIONS"])
def admin_endpoint():
    return {"admin": True}, 200


@api_key_required
def protected_endpoint():
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
