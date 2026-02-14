from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, Response, jsonify, make_response, request
from flask_jwt_extended import JWTManager, current_user, get_jwt, get_jwt_identity, verify_jwt_in_request

from core.auth.database_authenticator import DatabaseAuthenticator
from core.auth.dev_authenticator import DevAuthenticator
from core.auth.external_authenticator import ExternalAuthenticator
from core.auth.openid_authenticator import OpenIDAuthenticator
from core.config import Config
from core.log import logger
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User


current_authenticator = DatabaseAuthenticator()
jwt = JWTManager()


def cleanup_token_blacklist(app):
    with app.app_context():
        TokenBlacklist.delete_older(datetime.now() - timedelta(days=1))


def initialize(app: Flask):
    global current_authenticator
    global jwt

    jwt.init_app(app)

    authenticator = app.config.get("TARANIS_AUTHENTICATOR", None)
    if authenticator == "openid":
        current_authenticator = OpenIDAuthenticator(app)
    elif authenticator == "database":
        current_authenticator = DatabaseAuthenticator()
    elif authenticator == "dev":
        current_authenticator = DevAuthenticator()
    elif authenticator == "external":
        current_authenticator = ExternalAuthenticator()
    else:
        raise ValueError(f"Unknown authenticator: {authenticator}")


def authenticate(credentials: dict[str, str]) -> Response:
    return current_authenticator.authenticate(credentials)


def change_password(old_password: str, new_password: str, confirm_password: str) -> Response:
    try:
        if Config.TARANIS_AUTHENTICATOR != "database":
            return make_response({"error": "Password change is only supported with 'database' authenticator"}, 400)
        if new_password != confirm_password:
            return make_response({"error": "New password and confirm password do not match"}, 400)
        return DatabaseAuthenticator().change_password(current_user, old_password, new_password)
    except Exception:
        logger.exception("Error changing password")
        return make_response({"error": "Internal server error"}, 500)


def refresh(user: "User"):
    exp_timestamp = get_jwt()["exp"]
    now = datetime.now(timezone.utc)
    target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
    if target_timestamp > exp_timestamp:
        return current_authenticator.refresh(user)
    encoded_token = request.cookies.get("access_token_cookie")
    return jsonify({"access_token": encoded_token})


def logout(jti):
    return current_authenticator.logout(jti)


def auth_required(permissions: list | str | None = None):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({"error": "not authorized"}, 401)
            if permissions is None:
                permissions_set = set()
            elif isinstance(permissions, list):
                permissions_set = set(permissions)
            else:
                permissions_set = {permissions}

            try:
                verify_jwt_in_request()
            except Exception as ex:
                logger.exception(str(ex))
                return error

            user_name = get_jwt_identity()
            if not user_name:
                logger.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
                return error

            permission_claims = current_user.get_permissions()

            # is there at least one match with the permissions required by the call or no permissions required
            if permissions_set and not permissions_set.intersection(permission_claims):
                logger.store_auth_error_activity(
                    f"user {user_name} Insufficient permissions in JWT for identity",
                )
                return {"error": "forbidden"}, 403

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)
        auth_header = request.headers.get("Authorization", None)

        if not auth_header or not auth_header.startswith("Bearer"):
            logger.store_auth_error_activity("Missing Authorization Bearer")
            return error

        api_key = auth_header.replace("Bearer ", "")

        if Config.API_KEY.get_secret_value() != api_key:
            logger.store_auth_error_activity("Incorrect api key")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data[Config.JWT_IDENTITY_CLAIM]
    return User.find_by_name(identity) if identity else None


@jwt.user_identity_loader
def user_identity_lookup(user: "User") -> str:
    return user.username


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    return TokenBlacklist.invalid(jti)
