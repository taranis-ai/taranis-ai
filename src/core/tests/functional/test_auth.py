from flask_jwt_extended import create_access_token


class TestAuth:
    def test_auth_required_with_permissions(self, admin_user, non_admin_user, app_with_jwt_secret):
        from core.managers.auth_manager import auth_required

        non_admin_token = create_access_token(identity=non_admin_user)
        admin_token = create_access_token(identity=admin_user)

        @app_with_jwt_secret.route("/admin-test-endpoint")
        @auth_required(permissions=["ADMIN_OPERATIONS"])
        def admin_test():
            return {"admin": True}, 200

        client = app_with_jwt_secret.test_client()
        response = client.get(
            "/admin-test-endpoint",
            headers={"Authorization": f"Bearer {non_admin_token}"},
        )

        assert response.status_code == 403
        assert response.json == {"error": "forbidden"}

        response = client.get(
            "/admin-test-endpoint",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert response.json == {"admin": True}
