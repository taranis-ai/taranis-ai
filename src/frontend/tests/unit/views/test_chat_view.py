from datetime import UTC, datetime
from typing import Any

import pytest
from flask import url_for

from frontend.__init__ import create_app
from frontend.config import Config


CONVERSATION_ID = "01981234-5678-7abc-8def-0123456789ab"
MESSAGE_ID = "01981234-5678-7abc-8def-0123456789ac"


def _conversation(answer: str = "Summary") -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": CONVERSATION_ID,
        "title": "Vienna incidents",
        "created": now,
        "updated": now,
        "messages": [
            {
                "id": MESSAGE_ID,
                "role": "assistant",
                "content": answer,
                "created": now,
                "search_result": {
                    "filters": {"source": ["source-one", "source-two"], "range": "last7"},
                    "total_count": 12,
                    "story_ids": ["story-one"],
                },
            }
        ],
    }


@pytest.fixture(scope="session")
def app():
    return create_app({"TESTING": True, "DEBUG": True, "SERVER_NAME": "localhost", "CHAT_ENABLED": True})


def test_chat_history_escapes_answers_and_builds_doseq_assess_link(
    authenticated_client_basic,
    responses,
):
    conversation = _conversation('<img src=x onerror="alert(1)">\nSecond line')
    responses.get(f"{Config.TARANIS_CORE_URL}/chat/conversations", json={"items": [conversation]}, status=200)
    responses.get(f"{Config.TARANIS_CORE_URL}/chat/conversations/{CONVERSATION_ID}", json=conversation, status=200)

    response = authenticated_client_basic.get(url_for("chat.conversation", conversation_id=CONVERSATION_ID))

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;" in body
    assert '<img src=x onerror="alert(1)">' not in body
    assert "source=source-one&amp;source=source-two&amp;range=last7" in body
    assert "View 12 matching stories in Assess" in body
    assert 'data-testid="nav-chat"' in body
    assert 'hx-indicator="#chat-answer-loading"' in body
    assert 'data-testid="chat-answer-loading"' in body
    assert 'name="turn_id"' in body
    assert "!event.shiftKey && !event.isComposing" in body
    assert '<button id="chat-send" type="submit" class="btn btn-primary" data-testid="chat-send">Send</button>' in body


def test_new_chat_pushes_conversation_url(authenticated_client_basic, responses):
    conversation = _conversation()
    responses.post(
        f"{Config.TARANIS_CORE_URL}/chat/conversations",
        json={"conversation": conversation},
        status=201,
    )
    responses.get(f"{Config.TARANIS_CORE_URL}/chat/conversations", json={"items": [conversation]}, status=200)

    response = authenticated_client_basic.post(url_for("chat.send_message"), data={"content": "Vienna"})

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == url_for("chat.conversation", conversation_id=CONVERSATION_ID)
    assert 'data-testid="chat-message-assistant"' in response.get_data(as_text=True)


def test_chat_provider_error_keeps_draft_retryable(authenticated_client_basic, responses):
    responses.post(
        f"{Config.TARANIS_CORE_URL}/chat/conversations",
        json={"error": "Chat provider request failed"},
        status=502,
    )
    responses.get(f"{Config.TARANIS_CORE_URL}/chat/conversations", json={"items": []}, status=200)

    response = authenticated_client_basic.post(url_for("chat.send_message"), data={"content": "Retry me"})

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Chat provider request failed" in body
    assert ">Retry me</textarea>" in body


def test_delete_chat_refreshes_history(authenticated_client_basic, responses):
    responses.delete(f"{Config.TARANIS_CORE_URL}/chat/conversations/{CONVERSATION_ID}", json={"message": "deleted"}, status=200)
    responses.get(f"{Config.TARANIS_CORE_URL}/chat/conversations", json={"items": []}, status=200)

    response = authenticated_client_basic.delete(url_for("chat.delete_conversation", conversation_id=CONVERSATION_ID))

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == url_for("chat.index")
    assert "No saved conversations yet." in response.get_data(as_text=True)
