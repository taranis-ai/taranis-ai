from flask_jwt_extended import create_access_token, verify_jwt_in_request

from core.managers.auth_manager import auth_required


@auth_required(permissions=["ADMIN_OPERATIONS"])
def admin_endpoint():
    return {"admin": True}, 200


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
