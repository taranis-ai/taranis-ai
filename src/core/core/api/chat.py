from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.chat import ChatTurnRequest
from pydantic import ValidationError

from core.config import Config
from core.log import logger
from core.managers.auth_manager import auth_required
from core.managers.db_manager import db
from core.service.chat import (
    ChatConversationNotFoundError,
    ChatProviderError,
    ChatProviderTimeoutError,
    ChatService,
    ChatUnavailableError,
)


def _availability_error() -> tuple[dict[str, str], int] | None:
    if not Config.CHAT_ENABLED or not Config.CHAT_LLM_BASE_URL:
        return {"error": "Chat is not configured"}, 503
    return None


def _turn_error(exc: Exception) -> tuple[dict[str, str], int]:
    db.session.rollback()
    if isinstance(exc, ChatConversationNotFoundError):
        return {"error": "Chat conversation not found"}, 404
    if isinstance(exc, ChatUnavailableError):
        return {"error": "Chat is not configured"}, 503
    if isinstance(exc, ChatProviderError):
        logger.error("Chat request failed: %s", exc)
        if isinstance(exc, ChatProviderTimeoutError):
            return {"error": "Chat provider timed out"}, 504
        return {"error": "Chat provider request failed"}, 502
    logger.exception("Chat request failed")
    return {"error": "Chat request failed"}, 500


def _parse_turn() -> ChatTurnRequest | tuple[dict[str, str], int]:
    try:
        return ChatTurnRequest.model_validate(request.get_json(silent=True))
    except ValidationError as exc:
        message = exc.errors()[0].get("msg", "Invalid chat message") if exc.errors() else "Invalid chat message"
        return {"error": str(message)}, 400


class ChatConversations(MethodView):
    def get(self):
        return ChatService.list_conversations(current_user), 200

    def post(self):
        if isinstance(payload := _parse_turn(), tuple):
            return payload
        try:
            return {"conversation": ChatService.create_turn(current_user, payload.content)}, 201
        except Exception as exc:  # noqa: BLE001
            return _turn_error(exc)


class ChatConversation(MethodView):
    def get(self, conversation_id: str):
        try:
            return ChatService.get_conversation(conversation_id, current_user), 200
        except ChatConversationNotFoundError:
            return {"error": "Chat conversation not found"}, 404

    def delete(self, conversation_id: str):
        try:
            ChatService.delete_conversation(conversation_id, current_user)
            return {"message": "Chat conversation deleted"}, 200
        except ChatConversationNotFoundError:
            return {"error": "Chat conversation not found"}, 404


class ChatMessages(MethodView):
    def post(self, conversation_id: str):
        if isinstance(payload := _parse_turn(), tuple):
            return payload
        try:
            return {"conversation": ChatService.create_turn(current_user, payload.content, conversation_id)}, 201
        except Exception as exc:  # noqa: BLE001
            return _turn_error(exc)


def initialize(app: Flask):
    chat_bp = Blueprint("chat", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/chat")
    chat_bp.before_request(auth_required("ASSESS_ACCESS")(_availability_error))
    chat_bp.add_url_rule("/conversations", view_func=ChatConversations.as_view("conversations"))
    chat_bp.add_url_rule("/conversations/<string:conversation_id>", view_func=ChatConversation.as_view("conversation"))
    chat_bp.add_url_rule("/conversations/<string:conversation_id>/messages", view_func=ChatMessages.as_view("messages"))
    app.register_blueprint(chat_bp)
