import io
import json
import socket
import time
from threading import Event, Thread

import fakeredis
import pytest
import requests
from urllib3.connection import HTTPConnection
from urllib3.response import HTTPResponse

from core.model.settings import Settings
from core.service.chat import ChatClient, ChatProviderError, ChatProviderTimeoutError, ChatService
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
    settings = Settings.with_defaults(
        {"chat_llm_base_url": "https://llm.example/v1", "chat_llm_model": "test-model", "chat_llm_api_key": "test-secret"}
    )
    settings["llm_endpoints"]["existing-chat"]["api_formats"] = {request.param: {"model": "test-model"}}
    settings["llm_endpoints"]["existing-chat"]["enabled"] = True
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
        assert kwargs["headers"]["Authorization"] == "Bearer test-secret"
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


def test_turn_deadline_closes_continuously_streaming_response(configured_chat, monkeypatch):
    reader, writer = socket.socketpair()
    connection = HTTPConnection("localhost")
    connection.sock = reader
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "text/event-stream"
    response.raw = HTTPResponse(body=reader.makefile("rb"), preload_content=False, connection=connection, sock_shutdown=reader.shutdown)
    event = (
        {"choices": [{"index": 0, "delta": {"content": "Still streaming "}, "finish_reason": None}]}
        if configured_chat == "chat_completions"
        else {"type": "response.output_text.delta", "delta": "Still streaming "}
    )
    chunk = f"data: {json.dumps(event)}\n\n".encode()
    stopped = Event()

    def send_stream():
        try:
            until = time.monotonic() + 5
            while not stopped.is_set() and time.monotonic() < until:
                writer.sendall(chunk)
                stopped.wait(0.005)
        except OSError:
            pass
        finally:
            writer.close()

    sender = Thread(target=send_stream)
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    received = []
    sender.start()
    started = time.monotonic()
    try:
        with pytest.raises(ChatProviderTimeoutError):
            ChatClient(deadline=started + 1).create_response([], received.append)
        assert received
        assert response.raw.closed
        assert time.monotonic() - started < 3
    finally:
        stopped.set()
        response.close()
        reader.close()
        writer.close()
        sender.join(timeout=5)
    assert not sender.is_alive()


def test_hrag_turn_switching_partial_retrieval_and_live_history(configured_chat, db_persistent_session, admin_user, monkeypatch):
    from core.managers.db_manager import db
    from core.model.hrag import HragGeneration, HragMessage, HragWork
    from core.service.hrag import retrieval
    from core.service.hrag.indexing import fingerprint

    monkeypatch.setattr(retrieval.Config, "HRAG_ENABLED", True)
    story = create_story(news_items=[build_news_item_payload(content="Acme reported an incident.")])
    item = story.news_items[0]
    settings = Settings.get_settings()
    settings["llm_graph_planning_endpoint"] = "existing-chat"
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    generation = HragGeneration.from_dict(
        {
            "id": "chat-extraction-generation",
            "pipeline": "extraction",
            "active": True,
            "config": {"limit": 20000},
            "cursor": "",
            "scanned": True,
        }
    )
    db.session.add(generation)
    work = HragWork.from_dict(
        {
            "news_item_id": item.id,
            "generation_id": generation.id,
            "fingerprint": fingerprint(item, generation),
            "status": "ready",
            "result": {
                "entities": [{"id": "a", "type": "ORG", "name": "Acme", "evidence": {"start": 0, "end": 4, "quote": "Acme"}}],
                "relations": [],
            },
        }
    )
    db.session.add(work)
    db.session.commit()
    work_id, graph_key = work.id, work.graph_key
    graph_calls = []

    def graph_search(plan, keys, limit, timeout):
        graph_calls.append(keys)
        return [[{"key": graph_key, "work_id": work_id, "idx": None}]]

    monkeypatch.setattr(retrieval, "graph_search", graph_search)
    contexts = []

    def post(*args, **kwargs):
        payload = kwargs["json"]
        messages = payload.get("messages") or payload["input"]
        context = json.loads(messages[-1]["content"])
        contexts.append(context)
        if "text" in payload or "response_format" in payload:
            answer = json.dumps({"names": ["Acme"], "hops": 0})
        elif "retrieval" in context:
            assert context["retrieval"]["evidence"][0]["quote"] == "Acme"
            answer = "Acme is mentioned [G1]."
        else:
            answer = "Continuing in Chat."
        return _chat_response(answer) if configured_chat == "chat_completions" else _response({"output_text": answer})

    monkeypatch.setattr(requests, "post", post)
    conversation = None
    try:
        conversation = ChatService.create_turn(admin_user, "What is known about Acme?", "hrag-turn", mode="hrag")
        answer = conversation["messages"][-1]
        assert answer["mode"] == "hrag" and answer["hrag_result"]["evidence"][0]["citation"] == "G1"
        assert any("Vector retrieval is unavailable" in notice for notice in answer["hrag_result"]["notices"])
        assert graph_calls == [[graph_key]]
        metadata = db.session.get(HragMessage, answer["id"]).metadata_json
        assert "quote" not in json.dumps(metadata) and "Acme" not in json.dumps(metadata)
        followup = ChatService.create_turn(admin_user, "Continue", "chat-turn", conversation["id"])
        assert followup["messages"][-1]["content"] == "Continuing in Chat."
        assert contexts[-1]["conversation"][-1]["content"] == "Acme is mentioned [G1]."
        item.content = "Changed evidence."
        db.session.commit()
        saved = ChatService.get_conversation(conversation["id"], admin_user)
        assert saved["messages"][1]["hrag_result"]["evidence"] == []
        assert "no longer accessible" in saved["messages"][1]["content"]
        # The in-process Redis fake lacks Lua lock release; real Redis is covered by the browser flow.
        from core.managers.queue_manager import queue_manager

        queue_manager.redis.flushall()
        # Both unavailable branches fail without appending a half-turn.
        monkeypatch.setattr(retrieval, "graph_search", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))
        with pytest.raises(ChatProviderError):
            ChatService.create_turn(admin_user, "Try again", "failed-hrag", conversation["id"], mode="hrag")
        assert len(ChatService.get_conversation(conversation["id"], admin_user)["messages"]) == 4
    finally:
        if conversation:
            ChatService.delete_conversation(conversation["id"], admin_user)
        db.session.delete(generation)
        db.session.delete(story)
        db.session.commit()
