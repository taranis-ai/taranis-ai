from urllib.parse import quote
from flask import redirect, make_response, request, Flask
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt, verify_jwt_in_request


from core.managers import auth_manager


class Login(MethodView):
    @jwt_required()
    def get(self):
        return make_response(redirect(quote(request.args.get(key="gotoUrl", default="/"))))

    def post(self):
        if not request.json and not request.form:
            return {"error": "No data provided"}, 400

        username = request.json.get("username") if request.json else request.form.get("username")
        password = request.json.get("password") if request.json else request.form.get("password")

        if not username or not password:
            return {"error": "Missing username or password"}, 400

        credentials: dict[str, str] = {"username": username, "password": password}
        return auth_manager.authenticate(credentials)


class Refresh(MethodView):
    @jwt_required()
    def get(self):
        return auth_manager.refresh(auth_manager.get_user_from_jwt())


class Logout(MethodView):
    def get(self):
        try:
            verify_jwt_in_request()
            jti = get_jwt()["jti"]
            auth_manager.logout(jti)
            return {"message": "Successfully logged out"}, 200
        except Exception:
            return {"error": "Failed to log out"}, 500


def initialize(app: Flask):
    base_route = "/api/auth"
    app.add_url_rule(f"{base_route}/login", view_func=Login.as_view("login"))
    app.add_url_rule(f"{base_route}/refresh", view_func=Refresh.as_view("refresh"))
    app.add_url_rule(f"{base_route}/logout", view_func=Logout.as_view("logout"))
