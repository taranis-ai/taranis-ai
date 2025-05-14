from datetime import datetime, timedelta
from functools import wraps
from flask import Response, request, Flask
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, verify_jwt_in_request, current_user

from core.log import logger
from core.auth.openid_authenticator import OpenIDAuthenticator
from core.auth.dev_authenticator import DevAuthenticator
from core.auth.database_authenticator import DatabaseAuthenticator
from core.auth.external_authenticator import ExternalAuthenticator
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User

from core.config import Config

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


def refresh(user: "User"):
    return current_authenticator.refresh(user)


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

            identity = get_jwt_identity()
            if not identity:
                logger.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
                return error

            permission_claims = current_user.get_permissions()

            # is there at least one match with the permissions required by the call or no permissions required
            if permissions_set and not permissions_set.intersection(permission_claims):
                logger.store_auth_error_activity(
                    f"user {identity.name} [{identity.id}] Insufficient permissions in JWT for identity",
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
def user_identity_lookup(user: "User"):
    return user.username


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    return TokenBlacklist.invalid(jti)
