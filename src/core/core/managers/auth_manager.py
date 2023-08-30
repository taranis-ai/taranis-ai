from datetime import datetime, timedelta
from functools import wraps
from flask import request
from typing import Any
from flask_jwt_extended import (
    JWTManager,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import JWTExtendedException

# from core.managers import queue_manager
from core.managers.log_manager import logger
from core.auth.keycloak_authenticator import KeycloakAuthenticator
from core.auth.openid_authenticator import OpenIDAuthenticator
from core.auth.test_authenticator import TestAuthenticator
from core.auth.database_authenticator import DatabaseAuthenticator
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User
from core.config import Config

current_authenticator = TestAuthenticator()

api_key = Config.API_KEY


def cleanup_token_blacklist(app):
    with app.app_context():
        TokenBlacklist.delete_older(datetime.now() - timedelta(days=1))


def initialize(app):
    global current_authenticator

    JWTManager(app)

    authenticator = app.config.get("TARANIS_NG_AUTHENTICATOR", None)
    if authenticator == "openid":
        current_authenticator = OpenIDAuthenticator()
    elif authenticator == "keycloak":
        current_authenticator = KeycloakAuthenticator()
    elif authenticator == "database":
        current_authenticator = DatabaseAuthenticator()
    elif authenticator == "test":
        current_authenticator = TestAuthenticator()
    else:
        raise ValueError(f"Unknown authenticator: {authenticator}")

    with app.app_context():
        current_authenticator.initialize(app)

    # queue_manager.schedule_job_every_day("00:00", cleanup_token_blacklist)


def get_required_credentials():
    return current_authenticator.get_required_credentials()


def authenticate(credentials: dict[str, str]) -> tuple[dict[str, Any], int]:
    return current_authenticator.authenticate(credentials)


def refresh(user):
    return current_authenticator.refresh(user)


def logout(token):
    return current_authenticator.logout(token)


def no_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def auth_required(permissions: list | str):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({"error": "not authorized"}, 401)
            permissions_set = set(permissions) if isinstance(permissions, list) else {permissions}

            # do we have a JWT token?
            try:
                verify_jwt_in_request()
            except JWTExtendedException:
                logger.store_auth_error_activity("Missing JWT")
                return error

            # does it encode an identity?
            identity = get_jwt_identity()
            if not identity:
                logger.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
                return error

            # does it include permissions?
            claims = get_jwt()
            user_claims = claims.get("user_claims")
            if not user_claims:
                logger.store_user_auth_error_activity(identity, "", "Missing permissions in JWT for identity")
                return error

            permission_claims = set(user_claims.get("permissions"))

            # is there at least one match with the permissions required by the call?
            if not permissions_set.intersection(permission_claims):
                logger.store_user_auth_error_activity(
                    identity,
                    "",
                    "Insufficient permissions in JWT for identity",
                )
                return error

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)

        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            logger.store_auth_error_activity("Missing Authorization header")
            return error

        if not auth_header.startswith("Bearer"):
            logger.store_auth_error_activity("Missing Authorization Bearer")
            return error

        api_key = auth_header.replace("Bearer ", "")

        if Config.API_KEY != api_key:
            logger.store_auth_error_activity(f"Incorrect api key: {api_key}")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def get_access_key():
    return request.headers["Authorization"].replace("Bearer ", "")


def get_user_from_jwt() -> User | None:
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        logger.exception()
        return None
    identity = get_jwt_identity()

    return User.find_by_name(identity) if identity else None
