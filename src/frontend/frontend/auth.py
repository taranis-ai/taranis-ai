import contextlib
from functools import wraps
from typing import Any

from flask import Flask, Response, make_response, redirect, render_template, request, url_for
from flask_jwt_extended import JWTManager, current_user, get_jwt, get_jwt_identity, unset_jwt_cookies, verify_jwt_in_request
from models.user import UserProfile
from requests.models import Response as ReqResponse

from frontend.cache import add_user_to_cache, get_user_from_cache
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.utils.router_helpers import is_htmx_request


jwt = JWTManager()


def init(app: Flask) -> None:
    jwt.init_app(app)


def _login_url_with_next() -> str:
    login_url = url_for("base.login")

    if request.endpoint == "base.login":
        return login_url

    path = request.path or ""
    query_string = request.query_string.decode()

    next_target = path
    if query_string:
        next_target = f"{path}?{query_string}"

    if not next_target or next_target == login_url:
        return login_url

    return url_for("base.login", next=next_target)


def _redirect_to_login_response() -> ResponseReturnValue:
    login_url = _login_url_with_next()

    if is_htmx_request():
        return make_response("", 401, {"HX-Redirect": login_url})

    return make_response(redirect(login_url, code=302))


def _clear_jwt_cookies(response):
    response.delete_cookie(Config.JWT_ACCESS_COOKIE_NAME)
    unset_jwt_cookies(response)
    return response


def _unauthorized_response(clear_cookies: bool = False) -> ResponseReturnValue:
    response = _redirect_to_login_response()
    return _clear_jwt_cookies(response) if clear_cookies else response


# def authenticate(credentials: dict[str, str]) -> Response:
#     return current_authenticator.authenticate(credentials)


# def refresh(user: "UserProfile"):
#     return current_authenticator.refresh(user)


def logout() -> tuple[str, int] | Response:
    error_msg = "Logout failed"
    try:
        core_response: ReqResponse = CoreApi().logout()
    except Exception as exc:
        # If the core isn't reachable, fall back to the login page without crashing.
        logger.error(f"Core logout failed: {exc}")
        return render_template("login/index.html", login_error="Logout failed"), 500

    if not core_response.ok:
        with contextlib.suppress(Exception):
            error_msg = core_response.json().get("error", error_msg)
        return render_template("login/index.html", login_error=error_msg), core_response.status_code

    response = make_response("Session expired! Redirecting to Login Page")
    if is_htmx_request():
        response.headers["HX-Redirect"] = url_for("base.login")
    else:
        response.headers["Location"] = url_for("base.login")
        response.status_code = 302

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
                logger.info("JWT verification failed")
                return _unauthorized_response()

            user_name = get_jwt_identity()
            if not user_name:
                logger.error(f"Missing identity in JWT: {get_jwt()}")
                return _unauthorized_response()

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


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)
        auth_header = request.headers.get("Authorization", None)

        if not auth_header or not auth_header.startswith("Bearer"):
            logger.error("Missing Authorization Bearer")
            return error

        api_key = auth_header.replace("Bearer ", "")

        if Config.CORE_API_KEY.get_secret_value() != api_key:
            logger.error("Incorrect api key")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


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
    return _unauthorized_response(clear_cookies=True)


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return _unauthorized_response(clear_cookies=True)
