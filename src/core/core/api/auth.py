from flask import Blueprint, Flask, g, request
from flask.views import MethodView
from flask_jwt_extended import current_user, get_jwt, jwt_required

from core.api.contracts import validate_request
from core.auth.base_authenticator import BaseAuthenticator
from core.auth.external_authenticator import ExternalAuthenticator
from core.config import Config
from core.log import logger
from core.managers import auth_manager


def _login_payload():
    if Config.TARANIS_AUTHENTICATOR == "external":
        return ExternalAuthenticator.get_credentials(request.headers)
    data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    return data if isinstance(data, dict) and data else None


class Login(MethodView):
    @validate_request(load_body=_login_payload)
    def post(self):
        if g.api_body is None:
            return {"error": "No data provided"}, 400
        return auth_manager.authenticate(g.api_json)


class Refresh(MethodView):
    @jwt_required(locations=["headers"])
    @validate_request
    def get(self):
        return BaseAuthenticator.issue_access_token(current_user)


class Logout(MethodView):
    @jwt_required()
    @validate_request
    def delete(self):
        jti = get_jwt()["jti"]
        auth_manager.logout(jti)
        return {"message": "Successfully logged out"}, 200


class AuthMethod(MethodView):
    @validate_request
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
    @validate_request
    def post(self):
        logger.debug("Received request to change password")
        if not (json_data := g.api_body.model_dump(exclude_unset=True)):
            return {"error": "No input data provided"}, 400
        return auth_manager.change_password(
            json_data.get("current_password", ""), json_data.get("new_password", ""), json_data.get("confirm_password", "")
        )


def initialize(app: Flask):
    auth_bp = Blueprint("auth", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/auth")

    auth_bp.add_url_rule("/login", view_func=Login.as_view("login"))
    auth_bp.add_url_rule("/refresh", view_func=Refresh.as_view("refresh"))
    auth_bp.add_url_rule("/logout", view_func=Logout.as_view("logout"))
    auth_bp.add_url_rule("/method", view_func=AuthMethod.as_view("auth_method"))
    auth_bp.add_url_rule("/change_password", view_func=UserChangePassword.as_view("change_password"), methods=["POST"])

    app.register_blueprint(auth_bp)
