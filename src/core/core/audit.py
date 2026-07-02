import json
from datetime import datetime, timezone
from typing import Any

from flask import Flask, Response, g, request
from flask_jwt_extended import current_user as jwt_current_user

from core.config import Config
from core.log import logger


AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def init_app(app: Flask) -> None:
    app.after_request(after_request)


def after_request(response: Response) -> Response:
    try:
        if should_audit():
            write_event(build_event(response))
    except Exception:
        logger.exception("Failed to write audit log")
    return response


def should_audit() -> bool:
    if not Config.AUDIT_LOG_ENABLED:
        return False
    if request.method not in AUDIT_METHODS:
        return False
    if not is_api_path(request.path):
        return False
    return request.endpoint == "auth.login" or current_user() is not None


def build_event(response: Response) -> dict[str, Any]:
    user = None if request.endpoint == "auth.login" else current_user()
    event = {
        "event": "audit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.path,
        "endpoint": request.endpoint,
        "status": response.status_code,
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "organization_id": organization_id(user),
        "client_ip": client_ip(),
        "route_ids": route_ids(),
    }
    if user is None and request.endpoint == "auth.login":
        event["username"] = login_username()
    return event


def write_event(event: dict[str, Any]) -> None:
    print(json.dumps(event, sort_keys=True, separators=(",", ":")), flush=True)


def is_api_path(path: str) -> bool:
    api_root = f"{Config.APPLICATION_ROOT.rstrip('/')}/api"
    return path == api_root or path.startswith(f"{api_root}/")


def current_user():
    if hasattr(g, "authenticated_user"):
        return g.authenticated_user
    try:
        return jwt_current_user._get_current_object()
    except RuntimeError:
        return None


def organization_id(user) -> str | None:
    if user is None:
        return None
    organization = getattr(user, "organization", None)
    return getattr(organization, "id", None)


def client_ip() -> str | None:
    if forwarded := request.headers.get("X-Forwarded-For"):
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr


def route_ids() -> dict[str, str]:
    return {key: str(value) for key, value in (request.view_args or {}).items() if key == "id" or key.endswith("_id")}


def login_username() -> str | None:
    payload = request.get_json(silent=True) if request.is_json else None
    username = payload.get("username") if isinstance(payload, dict) else request.form.get("username")
    return username[:256] if isinstance(username, str) else None
