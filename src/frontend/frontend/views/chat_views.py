import re
import uuid
from typing import Any
from urllib.parse import urlencode

import requests
from flask import abort, current_app, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.chat import ChatConversation, ChatConversationList, ChatConversationSummary, ChatTurnRequest, ChatTurnResponse
from pydantic import ValidationError

from frontend.auth import auth_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView


class ChatView(BaseView):
    @staticmethod
    def _load_conversations() -> tuple[list[ChatConversationSummary], bool]:
        api = CoreApi()
        try:
            with api.api_download("/chat/conversations") as response:
                if response.status_code == 503:
                    return [], response.json().get("error") == "Chat is not configured"
                payload = api.check_response(response, "/chat/conversations")
        except requests.RequestException, ValueError:
            return [], False
        return (ChatConversationList.model_validate(payload).items if payload else []), False

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
            if message.hrag_result:
                citations = {}
                evidence_items = data["hrag_result"]["evidence"]
                known_ids = {evidence["citation"] for evidence in evidence_items}
                cited_ids = [match.group(1) for match in re.finditer(r"\[([GV]\d+)\]", message.content) if match.group(1) in known_ids]
                citation_order = dict.fromkeys([*cited_ids, *(evidence["citation"] for evidence in evidence_items)])
                numbers = {citation: number for number, citation in enumerate(citation_order, start=1)}
                for evidence in evidence_items:
                    evidence["assess_url"] = url_for("assess.assess") + "?" + urlencode({"story_ids": evidence["story_id"]})
                    evidence["citation_number"] = numbers[evidence["citation"]]
                    citations[evidence["citation"]] = evidence
                parts = []
                start = 0
                for match in re.finditer(r"\[([GV]\d+)\]", message.content):
                    if evidence := citations.get(match.group(1)):
                        parts.append({"text": message.content[start : match.start()]})
                        parts.append({"citation": evidence})
                        start = match.end()
                parts.append({"text": message.content[start:]})
                data["content_parts"] = parts
            messages.append(data)
        return messages

    @classmethod
    def _context(
        cls,
        conversation: ChatConversation | None = None,
        notification: str | None = None,
        draft: str = "",
        turn_id: str | None = None,
    ) -> dict[str, Any]:
        conversations, chat_not_configured = cls._load_conversations()
        return {
            "_show_sidebar": False,
            "conversations": conversations,
            "chat_not_configured": chat_not_configured,
            "conversation": conversation,
            "message_views": cls._message_views(conversation),
            "notification": notification,
            "draft": draft,
            "hrag_enabled": current_app.config.get("HRAG_ENABLED", False),
            "mode": request.form.get("mode") or (conversation.messages[-1].mode if conversation and conversation.messages else "chat"),
            "turn_id": turn_id or str(uuid.uuid7()),
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
            payload = ChatTurnRequest.model_validate(request.form)
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
                timeout=(5.0, Config.CHAT_REQUEST_TIMEOUT),
            )
        except requests.RequestException:
            conversation = cls._load_conversation(conversation_id) if conversation_id else None
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.render_response_notification({"error": "Chat request timed out or could not reach core."}),
                draft=draft,
                turn_id=str(payload.turn_id),
            ), 200

        if not response.ok:
            conversation = cls._load_conversation(conversation_id) if conversation_id else None
            return cls._render_workspace(
                conversation=conversation,
                notification=cls.get_notification_from_response(response),
                draft=draft,
                turn_id=str(payload.turn_id),
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
        try:
            response = CoreApi().api_delete(f"/chat/conversations/{conversation_id}")
        except requests.RequestException:
            return cls._render_workspace(
                conversation=cls._load_conversation(conversation_id),
                notification=cls.render_response_notification({"error": "Chat request timed out or could not reach core."}),
            ), 200
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
