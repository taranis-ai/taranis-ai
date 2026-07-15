from typing import Any
from urllib.parse import urlencode

import requests
from flask import abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.chat import ChatConversation, ChatConversationList, ChatConversationSummary, ChatTurnRequest, ChatTurnResponse
from pydantic import ValidationError

from frontend.auth import auth_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView


class ChatView(BaseView):
    @staticmethod
    def _load_conversations() -> list[ChatConversationSummary]:
        payload = CoreApi().api_get("/chat/conversations")
        return ChatConversationList.model_validate(payload).items if payload else []

    @staticmethod
    def _load_conversation(conversation_id: str) -> ChatConversation | None:
        payload = CoreApi().api_get(f"/chat/conversations/{conversation_id}")
        return ChatConversation.model_validate(payload) if payload else None

    @staticmethod
    def _message_views(conversation: ChatConversation | None) -> list[dict[str, Any]]:
        if not conversation:
            return []
        messages = []
        for message in conversation.messages:
            data = message.model_dump(mode="json")
            if result := message.search_result:
                query_string = urlencode(result.filters, doseq=True)
                assess_url = url_for("assess.assess")
                data["assess_url"] = f"{assess_url}?{query_string}" if query_string else assess_url
            messages.append(data)
        return messages

    @classmethod
    def _context(
        cls,
        conversation: ChatConversation | None = None,
        notification: str | None = None,
        draft: str = "",
    ) -> dict[str, Any]:
        return {
            "_show_sidebar": False,
            "conversations": cls._load_conversations(),
            "conversation": conversation,
            "message_views": cls._message_views(conversation),
            "notification": notification,
            "draft": draft,
        }

    @classmethod
    def _render_workspace(cls, **kwargs: Any) -> str:
        return render_template("chat/workspace.html", **cls._context(**kwargs))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def index(cls, conversation_id: str | None = None) -> ResponseReturnValue:
        conversation = cls._load_conversation(conversation_id) if conversation_id else None
        if conversation_id and not conversation:
            abort(404)
        return render_template("chat/index.html", **cls._context(conversation=conversation)), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def send_message(cls, conversation_id: str | None = None) -> ResponseReturnValue:
        draft = request.form.get("content", "")
        try:
            payload = ChatTurnRequest(content=draft)
        except ValidationError as exc:
            message = exc.errors()[0].get("msg", "Invalid chat message") if exc.errors() else "Invalid chat message"
            conversation = cls._load_conversation(conversation_id) if conversation_id else None
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.render_response_notification({"error": str(message)}),
                draft=draft,
            ), 200

        endpoint = f"/chat/conversations/{conversation_id}/messages" if conversation_id else "/chat/conversations"
        try:
            response = CoreApi().api_post(
                endpoint,
                json_data=payload.model_dump(mode="json"),
                timeout=Config.CHAT_REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            conversation = cls._load_conversation(conversation_id) if conversation_id else None
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.render_response_notification({"error": "Chat request timed out or could not reach core."}),
                draft=draft,
            ), 200

        if not response.ok:
            conversation = cls._load_conversation(conversation_id) if conversation_id else None
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.get_notification_from_response(response),
                draft=draft,
            ), 200

        turn = ChatTurnResponse.model_validate(response.json())
        rendered = cls._render_workspace(conversation=turn.conversation)
        response = make_response(rendered, 200)
        if not conversation_id:
            response.headers["HX-Push-Url"] = url_for("chat.conversation", conversation_id=turn.conversation.id)
        return response

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def delete_conversation(cls, conversation_id: str) -> ResponseReturnValue:
        response = CoreApi().api_delete(f"/chat/conversations/{conversation_id}")
        if not response.ok:
            conversation = cls._load_conversation(conversation_id)
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.get_notification_from_response(response),
            ), 200

        rendered = cls._render_workspace()
        result = make_response(rendered, 200)
        result.headers["HX-Push-Url"] = url_for("chat.index")
        return result
