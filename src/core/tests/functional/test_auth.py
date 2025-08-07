from flask_jwt_extended import verify_jwt_in_request


class TestAuth:
    def test_auth_required_with_permissions(self, app, admin_user, non_admin_user):
        from core.managers.auth_manager import auth_required
        from flask_jwt_extended import create_access_token

        @auth_required(permissions=["ADMIN_OPERATIONS"])
        def dummy_protected():
            return {"admin": True}, 200

        # non-admin test
        token = create_access_token(identity=non_admin_user)
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            verify_jwt_in_request()
            response = dummy_protected()
            assert response == ({"error": "forbidden"}, 403)

        # admin test
        token = create_access_token(identity=admin_user)
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            verify_jwt_in_request()
            response = dummy_protected()
            assert response == ({"admin": True}, 200)
