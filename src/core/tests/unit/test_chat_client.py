import io
import json
import time
from contextlib import suppress
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import fakeredis
import pytest
import requests
from models.assess import ASSESS_FILTER_MULTI_KEYS, AssessSearchFilters
from models.chat import ChatAnswerResponse, ChatPlannerResponse

from core.config import Config
from core.model.settings import Settings
from core.service.chat import (
    ANSWER_PROMPT,
    CHAT_TURN_TIMEOUT_SECONDS,
    PLANNER_PROMPT,
    ChatProviderError,
    ChatProviderTimeoutError,
    ChatService,
    ChatTurnStream,
    ChatUnavailableError,
    ResponsesClient,
)


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
    response.headers["Content-Type"] = "text/event-stream; charset=utf-8"
    response.raw = io.BytesIO("".join(f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events).encode())
    return response


@pytest.fixture
def configured_chat(monkeypatch):
    settings = Settings.with_defaults(
        {
            "chat_llm_base_url": "https://llm.example/v1/",
            "chat_llm_api_key": "test-secret",
            "chat_llm_model": "test-model",
            "chat_llm_timeout": 42,
        }
    )
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    return settings


def test_responses_client_sends_auth_schema_model_and_timeout(configured_chat, monkeypatch):
    captured = {}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return _response({"output_text": '{"answer":"Hello"}'})

    monkeypatch.setattr(requests, "post", post)

    result = ResponsesClient().create_structured({"question": "Hi"}, "Answer", ChatAnswerResponse)

    assert result.answer == "Hello"
    assert captured["url"] == "https://llm.example/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["timeout"] == (5.0, 42)
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["store"] is False
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True
    schema = captured["json"]["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    planner_schema = ResponsesClient._strict_json_schema(ChatPlannerResponse)
    filter_schema = planner_schema["$defs"]["AssessSearchFilters"]
    assert filter_schema["additionalProperties"] is False
    assert set(filter_schema["required"]) == set(filter_schema["properties"])


def test_responses_client_reads_structured_message_output(configured_chat, monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _response(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"answer":"Nested"}'}],
                    }
                ]
            }
        ),
    )

    assert ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse).answer == "Nested"


def test_responses_client_streams_text_deltas(configured_chat, monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _stream_response(
            {"type": "response.output_text.delta", "delta": "Grü"},
            {"type": "response.output_text.delta", "delta": "ße"},
            {"type": "response.completed", "response": {"status": "completed"}},
        ),
    )
    deltas = []

    answer = ResponsesClient().create_text_stream({"question": "Hi"}, "Answer", deltas.append)

    assert answer == "Grüße"
    assert deltas == ["Grü", "ße"]


def test_responses_client_falls_back_only_when_streaming_is_rejected(configured_chat, monkeypatch):
    responses = iter([_response({}, status=422), _response({"output_text": '{"answer":"Fallback"}'})])
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs["json"])
        return next(responses)

    monkeypatch.setattr(requests, "post", post)
    deltas = []

    assert ResponsesClient().create_text_stream({}, "Answer", deltas.append) == "Fallback"
    assert deltas == ["Fallback"]
    assert calls[0]["stream"] is True
    assert calls[1]["text"]["format"]["type"] == "json_schema"


@pytest.mark.parametrize(
    ("invalid", "corrected", "response_model", "field", "error_type"),
    [
        ("not json", {"answer": "Repaired"}, ChatAnswerResponse, "<root>", "json_invalid"),
        (
            json.dumps({"mode": "search", "filters": {"language": None}}),
            {"mode": "search", "filters": {"language": ["de"]}},
            ChatPlannerResponse,
            "filters.language",
            "list_type",
        ),
    ],
)
def test_responses_client_retries_invalid_structured_output_once(
    configured_chat, monkeypatch, caplog, invalid, corrected, response_model, field, error_type
):
    responses = iter([_response({"output_text": invalid}), _response({"output_text": json.dumps(corrected)})])
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs["json"])
        return next(responses)

    monkeypatch.setattr(requests, "post", post)

    result = ResponsesClient().create_structured({}, "Answer", response_model)

    assert result == response_model.model_validate(corrected)
    assert len(calls) == 2
    assert "previous response was invalid" in calls[1]["instructions"]
    assert f"stage=schema field={field} type={error_type} attempt=1" in caplog.text
    assert invalid not in caplog.text


@pytest.mark.parametrize(
    ("field", "value", "error_type"),
    [(field, value, "list_type") for field in sorted(ASSESS_FILTER_MULTI_KEYS) for value in (None, "private-value", {"private-key": []})]
    + [(field, [None], "string_type") for field in sorted(ASSESS_FILTER_MULTI_KEYS)]
    + [(field, "private-value", "bool_parsing") for field in ("read", "important", "relevant", "in_report")]
    + [(field, "private-value", "literal_error") for field in ("cybersecurity", "changed_by", "sort")]
    + [("range", "last0", "string_pattern_mismatch"), ("search", ["private-value"], "string_type")]
    + [(field, "private-value", "datetime_from_date_parsing") for field in ("timefrom", "timeto")]
    + [("private-key", "private-value", "extra_forbidden")],
)
def test_responses_client_rejects_repeated_invalid_filters_without_logging_content(
    configured_chat, monkeypatch, caplog, field, value, error_type
):
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs["json"])
        return _response({"output_text": json.dumps({"mode": "search", "filters": {field: value}})})

    monkeypatch.setattr(requests, "post", post)

    with pytest.raises(ChatProviderError, match="Chat provider returned an invalid response"):
        ResponsesClient().create_structured({}, PLANNER_PROMPT, ChatPlannerResponse)

    assert len(calls) == 2
    safe_field = "*" if field == "private-key" else field
    if error_type == "string_type" and field in ASSESS_FILTER_MULTI_KEYS:
        safe_field += ".*"
    for attempt in (1, 2):
        assert f"stage=schema field=filters.{safe_field} type={error_type} attempt={attempt}" in caplog.text
    assert "private-value" not in caplog.text
    assert "private-key" not in caplog.text
    assert configured_chat["chat_llm_api_key"] not in caplog.text


def test_responses_client_maps_missing_config_timeout_and_sanitized_failures(configured_chat, monkeypatch):
    configured_chat["chat_llm_base_url"] = ""
    with pytest.raises(ChatUnavailableError):
        ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)

    configured_chat["chat_llm_base_url"] = "https://llm.example"
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("provider detail")))
    with pytest.raises(ChatProviderTimeoutError, match="timed out"):
        ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: _response({"secret": "provider detail"}, status=500))
    with pytest.raises(ChatProviderError, match="HTTP 500") as error:
        ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)
    assert "provider detail" not in str(error.value)

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: _response({"status": "incomplete", "output_text": "partial"}))
    with pytest.raises(ChatProviderError, match="did not complete"):
        ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)


def test_chat_search_converts_naive_analyst_time_to_utc():
    filters = AssessSearchFilters(timefrom=datetime(2026, 7, 15, 9, 30))

    assert ChatService._query_params(filters, "Europe/Vienna")["timefrom"] == "2026-07-15T07:30:00"


def test_no_results_answer_uses_supported_analyst_locale():
    assert ChatService._no_results_answer({"language": "de-AT"}) == "Keine passenden Stories gefunden."


def test_chat_prompts_route_current_story_counts_through_search():
    assert "counts, statistics" in PLANNER_PROMPT
    assert "common translated equivalents with OR" in PLANNER_PROMPT
    assert 'search for "cyberattack OR Cyberangriff"' in PLANNER_PROMPT
    assert "never claim otherwise" in PLANNER_PROMPT
    assert "total_count is the authoritative number" in ANSWER_PROMPT


@pytest.mark.parametrize(
    ("field", "value"),
    [(field, ["private-value"]) for field in sorted(ASSESS_FILTER_MULTI_KEYS)] + [("search", "null"), ("search", " NULL ")],
)
def test_planner_repairs_invalid_catalog_and_story_references(configured_chat, monkeypatch, caplog, field, value):
    catalog = {
        "sources": [{"id": "source-one", "name": "Source One"}],
        "groups": [],
        "tags": ["apt"],
        "languages": ["en"],
    }
    responses = iter(
        [
            _response({"output_text": json.dumps({"mode": "search", "filters": {field: value}})}),
            _response({"output_text": json.dumps({"mode": "search", "filters": {"language": ["EN"]}})}),
        ]
    )
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: next(responses))
    result = ResponsesClient().create_structured(
        {}, PLANNER_PROMPT, ChatPlannerResponse, validator=lambda planner: ChatService._validate_planner(planner, catalog, {"known-story"})
    )
    assert result.filters.language == ["en"]
    assert f"stage=validator field=filters.{field} type=value_error attempt=1" in caplog.text
    assert "private-value" not in caplog.text


def test_chat_turn_stream_publishes_cumulative_throttled_snapshots(monkeypatch):
    monkeypatch.setattr(Config, "REALTIME_ENABLED", True)
    published = []
    monkeypatch.setattr("core.service.chat.realtime_publisher.publish", lambda *args, **kwargs: published.append((args, kwargs)) or True)
    now = iter([100.0, 100.1, 100.21])
    monkeypatch.setattr("core.service.chat.time.monotonic", lambda: next(now))
    stream = ChatTurnStream("user-id", "turn-id")

    stream.stage("answering")
    stream.add("One")
    stream.add(" two")
    stream.add(" three")
    stream.complete()

    assert published[0][0][:3] == ("user:#user-id", "chat.turn.updated", "updated")
    assert [call[1]["data"]["content"] for call in published] == ["", "One", "One two three", "One two three"]
    assert [call[1]["data"]["stage"] for call in published] == ["answering", "answering", "answering", "completed"]


class StreamingProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/headers/responses":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream" if self.path == "/stream/responses" else "application/json")
            self.end_headers()
        with suppress(BrokenPipeError, ConnectionResetError):
            while not self.server.stop.wait(0.01):
                self.wfile.write(b": keepalive\n\n" if self.path == "/stream/responses" else b" ")
                self.wfile.flush()

    def log_message(self, *args):
        pass


@pytest.fixture
def streaming_provider():
    server = ThreadingHTTPServer(("127.0.0.1", 0), StreamingProviderHandler)
    server.stop = Event()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.stop.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("mode", ["stream", "structured", "headers"])
def test_provider_deadline_bounds_continuous_network_reads(configured_chat, streaming_provider, mode):
    configured_chat["chat_llm_base_url"] = f"{streaming_provider}/{mode}"
    started = time.monotonic()
    client = ResponsesClient(deadline=started + 0.2)

    with pytest.raises(ChatProviderTimeoutError, match="Chat provider timed out"):
        if mode == "structured":
            client.create_structured({}, "Answer", ChatAnswerResponse)
        else:
            client.create_text_stream({}, "Answer", lambda delta: None)

    assert time.monotonic() - started < 2
    assert client.request_timeout == (5.0, 42)


def test_turn_lease_covers_deadline(app, monkeypatch):
    redis = fakeredis.FakeRedis()
    monkeypatch.setattr("core.service.chat.queue_manager.queue_manager._redis", redis)
    key = "taranis:chat:turn:conversation:conversation-id"

    with ChatService._turn_lease("user-id", "conversation-id"):
        assert redis.ttl(key) > CHAT_TURN_TIMEOUT_SECONDS
        assert not redis.lock(key).acquire(blocking=False)
