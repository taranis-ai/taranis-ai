from functools import wraps

from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, verify_jwt_in_request, current_user
from admin.config import Config
from admin.log import logger

jwt = JWTManager()


def init(app):
    jwt.init_app(app)


# def authenticate(credentials: dict[str, str]) -> Response:
#     return current_authenticator.authenticate(credentials)


# def refresh(user: "User"):
#     return current_authenticator.refresh(user)


# def logout(jti):
#     return current_authenticator.logout(jti)


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
                logger.error(f"Missing identity in JWT: {get_jwt()}")
                return error

            permission_claims = current_user.get_permissions()

            # is there at least one match with the permissions required by the call or no permissions required
            if permissions_set and not permissions_set.intersection(permission_claims):
                logger.error(
                    f"user {identity.name} [{identity.id}] Insufficient permissions in JWT for identity",
                )
                return {"error": "forbidden"}, 403

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


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
