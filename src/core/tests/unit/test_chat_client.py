import json
from datetime import datetime

import pytest
import requests
from models.assess import AssessSearchFilters
from models.chat import ChatAnswerResponse, ChatPlannerResponse
from pydantic import SecretStr

from core.config import Config
from core.service.chat import (
    ANSWER_PROMPT,
    PLANNER_PROMPT,
    ChatProviderError,
    ChatProviderTimeoutError,
    ChatService,
    ChatUnavailableError,
    ResponsesClient,
)


def _response(payload: dict, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode()
    return response


@pytest.fixture
def configured_chat(monkeypatch):
    monkeypatch.setattr(Config, "CHAT_LLM_BASE_URL", "https://llm.example/v1/")
    monkeypatch.setattr(Config, "CHAT_LLM_API_KEY", SecretStr("test-secret"))
    monkeypatch.setattr(Config, "CHAT_LLM_MODEL", "test-model")
    monkeypatch.setattr(Config, "CHAT_LLM_TIMEOUT", 42)


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
    assert captured["timeout"] == 42
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


def test_responses_client_retries_invalid_structured_output_once(configured_chat, monkeypatch):
    responses = iter([_response({"output_text": "not json"}), _response({"output_text": '{"answer":"Repaired"}'})])
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs["json"])
        return next(responses)

    monkeypatch.setattr(requests, "post", post)

    result = ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)

    assert result.answer == "Repaired"
    assert len(calls) == 2
    assert "previous response was invalid" in calls[1]["instructions"]


def test_responses_client_maps_missing_config_timeout_and_sanitized_failures(monkeypatch):
    monkeypatch.setattr(Config, "CHAT_LLM_BASE_URL", "")
    with pytest.raises(ChatUnavailableError):
        ResponsesClient().create_structured({}, "Answer", ChatAnswerResponse)

    monkeypatch.setattr(Config, "CHAT_LLM_BASE_URL", "https://llm.example")
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


def test_planner_rejects_hallucinated_catalog_and_story_references():
    catalog = {
        "sources": [{"id": "source-one", "name": "Source One"}],
        "groups": [],
        "tags": ["apt"],
        "languages": ["en"],
    }
    hallucinated_source = ChatPlannerResponse(
        mode="search",
        answer="ignored",
        filters=AssessSearchFilters(source=["made-up-source"]),
    )
    with pytest.raises(ValueError, match="Unknown source"):
        ChatService._validate_planner(hallucinated_source, catalog, set())

    hallucinated_story = ChatPlannerResponse(
        mode="search",
        answer="ignored",
        filters=AssessSearchFilters(story_ids=["made-up-story"]),
    )
    with pytest.raises(ValueError, match="Unknown recent story IDs"):
        ChatService._validate_planner(hallucinated_story, catalog, {"known-story"})

    string_null = ChatPlannerResponse(mode="search", answer="ignored", filters=AssessSearchFilters(search="null"))
    with pytest.raises(ValueError, match="must use JSON null"):
        ChatService._validate_planner(string_null, catalog, set())
