from datetime import datetime, timedelta, timezone
from functools import wraps
from hmac import compare_digest

from flask import Flask, Response, g, jsonify, make_response, request
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
AUTH_ERROR = ({"error": "not authorized"}, 401)


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
    permissions_set = _get_permissions_set(permissions)

    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if auth_error := _jwt_authorize(permissions_set):
                return auth_error

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _has_valid_api_key(log_failures=True):
            return AUTH_ERROR

        # allow
        return fn(*args, **kwargs)

    return wrapper


def _get_permissions_set(permissions: list | str | None) -> set[str]:
    if permissions is None:
        return set()
    return set(permissions) if isinstance(permissions, list) else {permissions}


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer"):
        return None

    provided_token = auth_header.removeprefix("Bearer").strip()
    return provided_token or None


def _has_valid_api_key(*, log_failures: bool = False) -> bool:
    if not (provided_token := _extract_bearer_token()):
        if log_failures:
            logger.store_auth_error_activity("Missing Authorization Bearer")
        return False

    if not compare_digest(Config.API_KEY.get_secret_value(), provided_token):
        if log_failures:
            logger.store_auth_error_activity("Incorrect api key")
        return False

    return True


def _jwt_authorize(permissions_set: set[str]) -> tuple[dict[str, str], int] | None:
    try:
        verify_jwt_in_request()
    except Exception as ex:
        logger.exception(str(ex))
        return AUTH_ERROR

    user_name = get_jwt_identity()
    if not user_name:
        logger.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
        return AUTH_ERROR

    permission_claims = current_user.get_permissions()
    if permissions_set and not permissions_set.intersection(permission_claims):
        logger.store_auth_error_activity(
            f"user {user_name} Insufficient permissions in JWT for identity",
        )
        return {"error": "forbidden"}, 403

    g.authenticated_user = current_user
    return None


def api_key_or_auth_required(permissions: list | str | None = None):
    permissions_set = _get_permissions_set(permissions)

    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if _has_valid_api_key(log_failures=False):
                g.authenticated_user = None
                return fn(*args, **kwargs)

            if auth_error := _jwt_authorize(permissions_set):
                _has_valid_api_key(log_failures=True)
                return auth_error

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


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
