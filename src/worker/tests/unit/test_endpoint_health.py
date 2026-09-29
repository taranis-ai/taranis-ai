import pytest
from niquests.exceptions import ConnectionError

from worker.config import Config
from worker.endpoint_health import check_endpoint


@pytest.mark.parametrize(
    ("kind", "config", "url", "result"),
    [
        (
            "llm",
            {"base_url": "http://model.test/v1", "api_format": "responses", "model": "test-model", "api_key": "test-secret", "timeout": 10},
            "http://model.test/v1/responses",
            {"status": "completed", "error": None, "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}]},
        ),
        (
            "llm",
            {"base_url": "http://model.test/v1", "api_format": "chat_completions", "timeout": 10},
            "http://model.test/v1/chat/completions",
            {"choices": [{"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}]},
        ),
        ("bot", {"type": "nlp_bot", "parameters": {"BOT_ENDPOINT": "http://bot.test/ner"}}, "http://bot.test/ner/", {"Austria": "location"}),
        (
            "bot",
            {"type": "sentiment_analysis_bot", "parameters": {"BOT_ENDPOINT": "http://bot.test/sentiment"}},
            "http://bot.test/sentiment/",
            {"sentiment": {"label": "neutral", "score": 0.9}},
        ),
        (
            "bot",
            {"type": "cybersec_classifier_bot", "parameters": {"BOT_ENDPOINT": "http://bot.test/classify"}},
            "http://bot.test/classify/",
            {"cybersecurity": 0.1, "non-cybersecurity": 0.9},
        ),
    ],
)
def test_endpoint_check_failure_and_recovery(requests_mock, kind, config, url, result):
    route = f"{Config.TARANIS_CORE_URL}/worker/endpoint-health/{kind}/test-id"
    requests_mock.get(route, json={"config": config})
    saved = requests_mock.post(route, json={"accepted": True})
    upstream = requests_mock.post(
        url,
        [
            {"exc": ConnectionError("private exception detail")},
            {"status_code": 401, "text": "private upstream detail"},
            {"json": {"unexpected": 123}},
            {"json": result},
        ],
    )
    for _ in range(3):
        with pytest.raises(RuntimeError, match="^Endpoint check failed$"):
            check_endpoint(kind, "test-id", "current-generation")
        assert saved.last_request.json() == {"generation": "current-generation", "healthy": False}
    check_endpoint(kind, "test-id", "current-generation")
    assert saved.last_request.json()["healthy"] is True
    if config.get("api_key"):
        assert upstream.last_request.headers["Authorization"] == "Bearer test-secret"
        assert upstream.last_request.json()["model"] == "test-model"
    requests_mock.get(route, json={"skip": True})
    check_endpoint(kind, "test-id", "old-generation")
    assert upstream.call_count == 4
