import time
from hmac import compare_digest

from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from core.config import Config
from core.log import logger
from core.managers.auth_manager import auth_required
from core.managers.realtime_publisher import realtime_publisher
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User


AUTHENTICATION_DISCONNECT = {"disconnect": {"code": 4501, "reason": "unauthorized"}}


class BroadcastNotification(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        payload = request.get_json(silent=True)
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not message.strip():
            return {"error": "Message is required"}, 400
        if len(message) > 500:
            return {"error": "Message must not exceed 500 characters"}, 400
        if not realtime_publisher.broadcast_notification(message):
            return {"error": "Broadcast could not be sent"}, 503
        return {"message": "Broadcast sent"}, 200


class ConnectedClients(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        clients = realtime_publisher.connected_clients()
        if clients is None:
            return {"error": "Connected clients are unavailable"}, 503

        user_ids = {client["user_id"] for client in clients if client["user_id"]}
        users = {user.id: user.username for user in User.get_bulk(list(user_ids))}
        return {
            "num_clients": len(clients),
            "num_users": len(user_ids),
            "clients": [{**client, "username": users.get(client["user_id"], "Unknown user")} for client in clients],
        }, 200


def connect():
    provided_secret = request.headers.get("X-Realtime-Proxy-Key", "")
    expected_secret = Config.CENTRIFUGO_CONNECT_PROXY_SECRET.get_secret_value()
    if not provided_secret or not compare_digest(provided_secret, expected_secret):
        logger.warning("realtime_connect_rejected %s", {"reason": "proxy_secret"})
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
    realtime_bp = Blueprint("realtime", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/realtime")
    realtime_bp.add_url_rule("/connect", methods=["POST"], view_func=connect)
    realtime_bp.add_url_rule("/broadcast", view_func=BroadcastNotification.as_view("broadcast_notification"))
    realtime_bp.add_url_rule("/clients", view_func=ConnectedClients.as_view("connected_clients"))
    app.register_blueprint(realtime_bp)
