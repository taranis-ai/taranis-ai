from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user, get_jwt, jwt_required

from core.auth.external_authenticator import ExternalAuthenticator
from core.config import Config
from core.log import logger
from core.managers import auth_manager


class Login(MethodView):
    def post(self):
        if Config.TARANIS_AUTHENTICATOR == "external":
            return auth_manager.authenticate(ExternalAuthenticator.get_credentials(request.headers))
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
        return auth_manager.refresh(current_user)


class Logout(MethodView):
    @jwt_required()
    def delete(self):
        jti = get_jwt()["jti"]
        auth_manager.logout(jti)
        return {"message": "Successfully logged out"}, 200


class AuthMethod(MethodView):
    def get(self):
        if Config.TARANIS_AUTHENTICATOR == "external":
            return {
                "auth_method": Config.TARANIS_AUTHENTICATOR,
                "auth_headers": {
                    "username_header": Config.EXTERNAL_AUTH_USER,
                    "roles_header": Config.EXTERNAL_AUTH_ROLES,
                    "name_header": Config.EXTERNAL_AUTH_NAME,
                    "organization_header": Config.EXTERNAL_AUTH_ORGANIZATION,
                },
            }
        return {"auth_method": Config.TARANIS_AUTHENTICATOR}, 200


class UserChangePassword(MethodView):
    @jwt_required()
    def post(self):
        logger.debug(f"Received request to change password. - {request.json}")
        if not (json_data := request.json):
            return {"error": "No input data provided"}, 400
        return auth_manager.change_password(json_data.get("current_password", ""), json_data.get("new_password", ""))


def initialize(app: Flask):
    auth_bp = Blueprint("auth", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/auth")

    auth_bp.add_url_rule("/login", view_func=Login.as_view("login"))
    auth_bp.add_url_rule("/refresh", view_func=Refresh.as_view("refresh"))
    auth_bp.add_url_rule("/logout", view_func=Logout.as_view("logout"))
    auth_bp.add_url_rule("/method", view_func=AuthMethod.as_view("auth_method"))
    auth_bp.add_url_rule("/change_password", view_func=UserChangePassword.as_view("change_password"), methods=["POST"])

    app.register_blueprint(auth_bp)
