import io
import json

import fakeredis
import pytest
import requests

from core.model.settings import Settings
from core.service.chat import ChatService, ResponsesClient
from tests.application.support.builders import build_news_item_payload, create_story


def _response(payload: dict, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode()
    response._content_consumed = True
    return response


def _stream_response(*events: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "text/event-stream"
    response.raw = io.BytesIO("".join(f"data: {json.dumps(event)}\n\n" for event in events).encode())
    return response


@pytest.fixture
def configured_chat(monkeypatch):
    settings = Settings.with_defaults({"chat_llm_base_url": "https://llm.example/v1", "chat_llm_model": "test-model"})
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    monkeypatch.setattr("core.service.chat.queue_manager.queue_manager._redis", fakeredis.FakeRedis())


def test_general_answer_streams_and_is_saved(configured_chat, admin_user, monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _stream_response(
            {"type": "response.output_text.delta", "delta": "Hello "},
            {"type": "response.output_text.delta", "delta": "there!"},
            {"type": "response.completed", "response": {"status": "completed"}},
        ),
    )

    conversation = ChatService.create_turn(admin_user, "Hello", "turn-id")
    try:
        saved = ChatService.get_conversation(conversation["id"], admin_user)
        assert [message["content"] for message in saved["messages"]] == ["Hello", "Hello there!"]
        assert saved["messages"][-1]["search_result"] is None
    finally:
        ChatService.delete_conversation(conversation["id"], admin_user)


def test_story_search_supplies_context_and_saves_answer(configured_chat, db_persistent_session, admin_user, monkeypatch):
    story = create_story(title="Chat lookup test", news_items=[build_news_item_payload()])
    story_id = story.id
    call = {"type": "function_call", "name": "search_stories", "call_id": "search-1", "arguments": "{}"}
    requests_sent = []

    def post(*args, **kwargs):
        requests_sent.append(kwargs["json"])
        if len(requests_sent) == 1:
            return _stream_response({"type": "response.completed", "response": {"status": "completed", "output": [call]}})
        context = json.loads(kwargs["json"]["input"][-1]["output"])
        assert story_id in [item["id"] for item in context["stories"]]
        assert context["total_count"] >= 1
        return _response({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Found your stories."}]}]})

    monkeypatch.setattr(requests, "post", post)
    conversation = ChatService.create_turn(admin_user, "Show recent stories", "turn-id")
    try:
        answer = ChatService.get_conversation(conversation["id"], admin_user)["messages"][-1]
        assert answer["content"] == "Found your stories."
        assert story_id in answer["search_result"]["story_ids"]
        assert len(requests_sent) == 2
    finally:
        ChatService.delete_conversation(conversation["id"], admin_user)
        db_persistent_session.delete(story)
        db_persistent_session.commit()


def test_search_without_matches_saves_no_results_answer(configured_chat, admin_user, monkeypatch):
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs)
        return _response(
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "search_stories",
                        "call_id": "search-1",
                        "arguments": json.dumps({"timefrom": "2999-01-01T00:00:00"}),
                    }
                ]
            }
        )

    monkeypatch.setattr(requests, "post", post)
    conversation = ChatService.create_turn(admin_user, "Stories from 2999", "turn-id")
    try:
        answer = ChatService.get_conversation(conversation["id"], admin_user)["messages"][-1]
        assert answer["search_result"]["total_count"] == 0
        assert answer["content"] in {"No matching stories found.", "Keine passenden Stories gefunden."}
        assert len(calls) == 1
    finally:
        ChatService.delete_conversation(conversation["id"], admin_user)


def test_answer_works_when_provider_does_not_support_streaming(configured_chat, monkeypatch):
    responses = iter([_response({}, status=422), _response({"output_text": "Hello"})])
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: next(responses))
    received = []

    result = ResponsesClient().create_response([], received.append)

    assert ResponsesClient.output_text(result) == "Hello"
    assert received == ["Hello"]
