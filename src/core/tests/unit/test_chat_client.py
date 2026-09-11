import io
import json

import fakeredis
import pytest
import requests

from core.model.settings import Settings
from core.service.chat import ChatClient, ChatProviderError, ChatService
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


def _chat_response(text: str) -> requests.Response:
    return _response({"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]})


def _chat_stream(*deltas: dict, finish_reason: str = "stop") -> requests.Response:
    response = _stream_response(
        *({"choices": [{"index": 0, "delta": delta, "finish_reason": None}]} for delta in deltas),
        {"choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]},
    )
    response.raw = io.BytesIO(response.raw.read() + b"data: [DONE]\n\n")
    return response


@pytest.fixture(params=["responses", "chat_completions"])
def configured_chat(monkeypatch, request):
    settings = Settings.with_defaults({"chat_llm_base_url": "https://llm.example/v1", "chat_llm_model": "test-model"})
    settings["chat_llm_api_format"] = request.param
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    monkeypatch.setattr("core.service.chat.queue_manager.queue_manager._redis", fakeredis.FakeRedis())
    return request.param


def test_general_answer_streams_and_is_saved(configured_chat, admin_user, monkeypatch):
    if configured_chat == "chat_completions":
        monkeypatch.setattr(
            requests,
            "post",
            lambda *args, **kwargs: _chat_stream(
                {"content": [{"type": "thinking", "thinking": [{"type": "text", "text": "Private reasoning"}]}]},
                {"content": "Hello "},
                {"content": "there!"},
            ),
        )
    else:
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
        # A disconnected follow-up must not save the partial answer or retry it.
        attempted = []

        def interrupted_post(*args, **kwargs):
            attempted.append(kwargs)
            event = (
                {"choices": [{"index": 0, "delta": {"content": "Partial answer"}, "finish_reason": None}]}
                if configured_chat == "chat_completions"
                else {"type": "response.output_text.delta", "delta": "Partial answer"}
            )
            return _stream_response(event)

        monkeypatch.setattr(requests, "post", interrupted_post)
        with pytest.raises(ChatProviderError):
            ChatService.create_turn(admin_user, "Continue", "interrupted-turn", conversation["id"])
        assert len(attempted) == 1
        assert ChatService.get_conversation(conversation["id"], admin_user)["messages"] == saved["messages"]
    finally:
        ChatService.delete_conversation(conversation["id"], admin_user)


def test_story_search_supplies_context_and_saves_answer(configured_chat, db_persistent_session, admin_user, monkeypatch):
    story = create_story(title="Chat lookup test", news_items=[build_news_item_payload()])
    story_id = story.id
    call = {"type": "function_call", "name": "search_stories", "call_id": "search-1", "arguments": "{}"}
    requests_sent = []

    def post(*args, **kwargs):
        assert args[0].endswith("/chat/completions" if configured_chat == "chat_completions" else "/responses")
        requests_sent.append(kwargs["json"])
        if len(requests_sent) == 1:
            if configured_chat == "chat_completions":
                assert "input" not in kwargs["json"] and "store" not in kwargs["json"]
                assert kwargs["json"]["tools"][0]["function"]["name"] == "search_stories"
                return _chat_stream(
                    {
                        "reasoning_content": "Private planning",
                        "tool_calls": [
                            {"index": 0, "id": "search001", "type": "function", "function": {"name": "search_stories", "arguments": "{"}}
                        ],
                    },
                    {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]},
                    finish_reason="tool_calls",
                )
            return _stream_response({"type": "response.completed", "response": {"status": "completed", "output": [call]}})
        if configured_chat == "chat_completions":
            messages = kwargs["json"]["messages"]
            assert messages[-2]["role"] == "assistant"
            assert messages[-2]["reasoning_content"] == "Private planning"
            assert messages[-2]["tool_calls"][0]["function"]["arguments"] == "{}"
            assert messages[-1]["role"] == "tool" and messages[-1]["tool_call_id"] == "search001"
            assert kwargs["json"]["tool_choice"] == "none" and "tools" not in kwargs["json"]
            context = json.loads(messages[-1]["content"])
        else:
            context = json.loads(kwargs["json"]["input"][-1]["output"])
        assert story_id in [item["id"] for item in context["stories"]]
        assert context["total_count"] >= 1
        if configured_chat == "chat_completions":
            return _chat_response("Found your stories.")
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


def test_answer_works_when_provider_does_not_support_streaming(configured_chat, monkeypatch):
    responses = iter(
        [_response({}, status=422), _chat_response("Hello") if configured_chat == "chat_completions" else _response({"output_text": "Hello"})]
    )
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: next(responses))
    received = []

    result = ChatClient().create_response([], received.append)

    assert ChatClient.output_text(result) == "Hello"
    assert received == ["Hello"]
