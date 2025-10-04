from requests.models import Response as ReqResponse
from functools import wraps
from flask import Flask
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, verify_jwt_in_request, current_user, unset_jwt_cookies
from flask import redirect, url_for, render_template, Response
from typing import Any

from frontend.config import Config
from frontend.log import logger
from frontend.cache import add_user_to_cache, get_user_from_cache
from frontend.utils.router_helpers import is_htmx_request
from frontend.core_api import CoreApi
from models.user import UserProfile

jwt = JWTManager()


def init(app: Flask) -> None:
    jwt.init_app(app)


# def authenticate(credentials: dict[str, str]) -> Response:
#     return current_authenticator.authenticate(credentials)


# def refresh(user: "UserProfile"):
#     return current_authenticator.refresh(user)


def logout() -> tuple[str, int] | Response:
    core_response: ReqResponse = CoreApi().logout()
    if not core_response.ok:
        return render_template("login/index.html", login_error=core_response.json().get("error")), core_response.status_code

    response = Response(status=302, headers={"Location": url_for("base.login")})
    if is_htmx_request():
        response = Response(status=200, headers={"HX-Redirect": url_for("base.login")})

    response.delete_cookie("access_token")
    unset_jwt_cookies(response)
    return response


def auth_required(permissions: list[str] | str | None = None):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs: dict[str, Any]):
            if permissions is None:
                permissions_set: set[str] = set()
            elif isinstance(permissions, list):
                permissions_set = set(permissions)
            else:
                permissions_set = {permissions}

            try:
                verify_jwt_in_request()
            except Exception:
                logger.exception("JWT verification failed")
                logger.debug("JWT verification failed")
                return redirect(url_for("base.login"), code=302)

            user_name = get_jwt_identity()
            if not user_name:
                logger.error(f"Missing identity in JWT: {get_jwt()}")
                return redirect(url_for("base.login"), code=302)

            permission_claims = current_user.permissions

            # is there at least one match with the permissions required by the call or no permissions required
            if permissions_set and not permissions_set.intersection(permission_claims):
                logger.error(
                    f"user {user_name} Insufficient permissions in JWT for identity",
                )
                return redirect("/forbidden", code=403)

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def update_current_user_cache() -> None | UserProfile:
    if result := CoreApi().api_get("/users"):
        return add_user_to_cache(user=result)
    return None


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data[Config.JWT_IDENTITY_CLAIM]
    return get_user_from_cache(identity) or update_current_user_cache()


@jwt.user_identity_loader
def user_identity_lookup(user: "UserProfile") -> str:
    return user.username


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict[str, Any]) -> bool:
    """
    jtw token blacklisting is handled by core
    cached userdata is invalidated, when userdata is changed
    """
    return False


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return redirect(url_for("base.login"), code=302)


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return redirect(url_for("base.login"), code=302)
