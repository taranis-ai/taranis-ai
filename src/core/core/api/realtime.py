import time
from hmac import compare_digest

from flask import Blueprint, Flask, request
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from core.config import Config
from core.log import logger
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User


AUTHENTICATION_DISCONNECT = {"disconnect": {"code": 4501, "reason": "unauthorized"}}


def connect():
    provided_secret = request.headers.get("X-Realtime-Proxy-Key", "")
    expected_secret = Config.CENTRIFUGO_CONNECT_PROXY_SECRET.get_secret_value()
    if not provided_secret or not compare_digest(provided_secret, expected_secret):
        logger.warning("realtime_connect_rejected %s", {"reason": "proxy_secret"})
        return {"error": "forbidden"}, 403

    origin = request.headers.get("Origin", "")
    if not origin or origin not in Config.CENTRIFUGO_ALLOWED_ORIGINS.split():
        logger.warning("realtime_connect_rejected %s", {"reason": "origin"})
        return {"error": "forbidden"}, 403

    if not Config.REALTIME_ENABLED:
        return AUTHENTICATION_DISCONNECT, 200

    try:
        claims = decode_token(request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME, ""))
    except (JWTExtendedException, PyJWTError):
        logger.warning("realtime_connect_rejected %s", {"reason": "authentication"})
        return AUTHENTICATION_DISCONNECT, 200

    if claims.get("type") != "access" or TokenBlacklist.invalid(claims.get("jti", "")):
        logger.warning("realtime_connect_rejected %s", {"reason": "authentication"})
        return AUTHENTICATION_DISCONNECT, 200

    identity = claims.get(Config.JWT_IDENTITY_CLAIM)
    user = User.find_by_name(identity) if isinstance(identity, str) else None
    if not user:
        logger.warning("realtime_connect_rejected %s", {"reason": "user"})
        return AUTHENTICATION_DISCONNECT, 200

    now = int(time.time())
    expire_at = min(int(claims.get("exp", 0)), now + 900)
    if expire_at <= now:
        return AUTHENTICATION_DISCONNECT, 200

    channels = ["global:events"]
    if user.organization_id:
        channels.append(f"org:{user.organization_id}")
    channels.append(f"user:#{user.id}")
    return {"result": {"user": user.id, "expire_at": expire_at, "channels": channels}}, 200


def initialize(app: Flask):
    realtime_bp = Blueprint("realtime", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/internal/realtime")
    realtime_bp.add_url_rule("/connect", methods=["POST"], view_func=connect)
    app.register_blueprint(realtime_bp)
