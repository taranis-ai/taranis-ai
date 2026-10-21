import json
from unittest.mock import patch

import pytest
from llm_bot.client import LLMClient
from llm_bot.config import Config as LLMConfig
from llm_bot.decisions_client import DecisionsClient
from llm_bot.schemas import ClassifyResponse
from models.classification import CLASSIFICATION_CATEGORIES
from rq import Retry

from worker.bots.base_bot import BaseBot
from worker.bots.bot_tasks import bot_task
from worker.bots.tagging_content import _news_item_content_for_tagging
from worker.config import Config


@pytest.mark.parametrize(
    "parameters, expected",
    [
        (
            {"ITEM_FILTER": "timefrom=2026-07-01T00%3A00%3A00"},
            {"timefrom": "2026-07-01T00:00:00", "worker": True, "exclude_attr": "BASE_BOT"},
        ),
        ({"filter": {"timefrom": "2026-07-01T00:00:00"}}, {"timefrom": "2026-07-01T00:00:00", "worker": True, "exclude_attr": "BASE_BOT"}),
        ({"filter": {"STORY_IDS": ["selected-story"]}}, {"story_ids": ["selected-story"]}),
        (
            {"ITEM_FILTER": "range=week&limit=2", "filter": {"SOURCE": "source", "STORY_IDS": ["changed-story"], "skip_processed": True}},
            {"source": "source", "story_ids": ["changed-story"], "worker": True, "exclude_attr": "BASE_BOT"},
        ),
    ],
)
def test_bot_story_filters_preserve_scope(parameters, expected):
    filter_dict = BaseBot().get_filter_dict(parameters)

    assert filter_dict == expected


def test_ioc_bot(stories, story_get_mock, requests_mock):
    from worker import bots

    ioc_bot = bots.IOCBot()
    uploads = requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/tags?replace=false", json={"message": "Tags updated"})
    result = ioc_bot.execute()

    item = next(item for story in stories for item in story["news_items"] if "CVE-2023-5678" in item["content"])
    assert result[item["id"]] == {"CVE-2023-5678": "cves"}
    assert {item["id"]: result[item["id"]]} in [request.json() for request in uploads.request_history]


@pytest.mark.parametrize("enabled", [True, False])
def test_story_bot_clusters_via_library(stories, requests_mock, monkeypatch, enabled):
    from worker import bots

    endpoint = {
        "name": "Clustering",
        "base_url": "https://llm.test/v1",
        "api_key": "provider-key",
        "model": "cluster-model",
        "api_format": "chat_completions",
        "timeout": 120,
        "enabled": enabled,
    }
    input_stories = [
        {**stories[0], "summary": "Short summary", "tags": {"security": {"name": "security", "tag_type": "misc"}}},
        {**stories[1], "summary": None, "tags": {}},
    ]
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=input_stories)
    parameters = {"llm_endpoint": endpoint, "REQUESTS_TIMEOUT": 17}

    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        if not enabled:
            from worker.llm import LLMConfigurationError

            with pytest.raises(LLMConfigurationError):
                bots.StoryBot().execute(parameters)
            provider.assert_not_called()
            return
        provider.return_value = {
            "output_text": json.dumps(
                {
                    "cluster_ids": {"event_clusters": [[1, 2]]},
                    "cluster_reasons": [{"story_ids": [1, 2], "reason": "Same event"}],
                    "message": "Processed",
                }
            )
        }
        result = bots.StoryBot().execute(parameters)

        assert result == {"message": "Processed", "changes": {"groups": [[story["id"] for story in input_stories]]}}
        provider.assert_awaited_once()
        client = provider.call_args.args[0]
        assert (client.base_url, client.api_key, client.model, client.api_mode, client.timeout) == (
            "https://llm.test/v1",
            "provider-key",
            "cluster-model",
            "chat_completions",
            17,
        )
        assert json.loads(provider.call_args.args[2]) == {
            "stories": [
                {"id": 1, "tags": {"security": "misc"}, "summary": "Short summary"},
                {"id": 2, "tags": {}, "summary": None},
            ]
        }

        provider.return_value = {
            "output_text": json.dumps({"cluster_ids": {"event_clusters": [[1], [2]]}, "cluster_reasons": [], "message": "Processed"})
        }
        assert bots.StoryBot().execute({"llm_endpoint": endpoint}) == {"message": "Processed. No clusters found."}
        assert provider.call_args.args[0].timeout == 120

        endpoint["model"] = ""
        endpoint["api_key"] = ""
        monkeypatch.setattr(LLMConfig, "LLM_MODEL", "ignored-environment-model")
        monkeypatch.setattr(LLMConfig, "LLM_API_KEY", "ignored-environment-key")
        bots.StoryBot().execute(parameters)
        assert provider.call_args.args[0].model == ""
        assert provider.call_args.args[0].api_key == ""

        provider.reset_mock()
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[])
        assert bots.StoryBot().execute(parameters) == {"message": "No new stories found"}
        provider.assert_not_awaited()


def test_analyst_bot_returns_meaningful_result_when_no_stories(monkeypatch):
    from worker import bots

    analyst_bot = bots.AnalystBot()
    monkeypatch.setattr(analyst_bot, "get_stories", lambda parameters: [])

    result = analyst_bot.execute({"REGULAR_EXPRESSION": "tag", "ATTRIBUTE_NAME": "label"})

    assert result == {"message": "No new stories found", "result": {}}


def test_news_item_content_for_tagging_handles_nullable_fields():
    news_item = {"title": None, "review": None, "content": "content"}

    assert _news_item_content_for_tagging(news_item) == "  content"
    assert _news_item_content_for_tagging(news_item, separator="\n") == "\n\ncontent"


def test_wordlist_bot_respects_false_override(monkeypatch):
    from worker import bots

    wordlist_bot = bots.WordlistBot()
    monkeypatch.setattr(wordlist_bot, "_get_word_list_entries", lambda: [{"value": "malware", "category": "new"}])
    monkeypatch.setattr(
        wordlist_bot,
        "get_stories",
        lambda _: [{"id": "story-1", "news_items": [{"id": "item-1", "content": "malware", "tags": {"malware": "existing"}}]}],
    )

    result = wordlist_bot.execute({"OVERRIDE_EXISTING_TAGS": False})

    assert result == {"item-1": {}}


def test_nlp_bot(stories, story_get_mock, requests_mock):
    from worker import bots

    endpoint = {"name": "NER", "base_url": "https://llm.test/v1", "timeout": 42}
    uploads = requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/tags?replace=false", json={"message": "Tags updated"})
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.return_value = {"output_text": '{"Microsoft": "ORG"}'}
        result = bots.NLPBot().execute({"llm_endpoint": endpoint, "REQUESTS_TIMEOUT": 17})
        assert result == {item["id"]: {"Microsoft": "ORG"} for story in stories for item in story["news_items"]}
        assert story_get_mock.call_count == 1
        assert provider.await_count == sum(len(story["news_items"]) for story in stories)
        assert uploads.call_count == provider.await_count
        assert uploads.last_request.json() == {stories[-1]["news_items"][-1]["id"]: {"Microsoft": "ORG"}}
        assert provider.call_args.args[0].timeout == 17
        assert provider.call_args.args[2] == _news_item_content_for_tagging(stories[-1]["news_items"][-1], separator="\n")
        assert "Cybersecurity mode is disabled" in provider.call_args.args[1]

        cyber_story = {**stories[-1], "attributes": {"classification": {"value": "security incident"}}}
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[cyber_story])
        bots.NLPBot().execute({"llm_endpoint": endpoint})
        assert "Cybersecurity mode is enabled" in provider.call_args.args[1]
        assert provider.call_args.args[0].timeout == 42


@pytest.mark.parametrize("multiple_items", [True, False])
def test_summary_bot_uses_library(stories, requests_mock, multiple_items):
    from worker import bots

    story = {**stories[0], "news_items": [stories[0]["news_items"][0]]}
    if multiple_items:
        story["news_items"].append(stories[1]["news_items"][0])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[story])
    endpoint = {
        "name": "Summary",
        "base_url": "https://summary.test/v1",
        "model": "summary-model",
        "api_key": "summary-key",
        "timeout": 42,
    }
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.side_effect = [{"output_text": '{"summary": "Concise summary"}'}, {"output_text": '{"title": "Generated title"}'}]
        result = bots.SummaryBot().execute({"llm_endpoint": endpoint})
        assert result["message"] == "Summarized 1 stories"
        assert provider.await_count == (2 if multiple_items else 1)
        client = provider.call_args.args[0]
        assert (client.base_url, client.model, client.api_key, client.timeout) == (
            "https://summary.test/v1",
            "summary-model",
            "summary-key",
            42,
        )
        expected = {"summary": "Concise summary"}
        if multiple_items:
            expected["title"] = "Generated title"
        assert result["changes"] == {
            "story_updates": {story["id"]: expected},
        }


def test_classification_bot(stories, requests_mock):
    from worker import bots

    assert tuple(field.alias or name for name, field in ClassifyResponse.model_fields.items()) == CLASSIFICATION_CATEGORIES
    items = [dict(item, id=f"classified-{index}") for index, item in enumerate(stories[0]["news_items"][:1] * 4)]
    items[-1]["content"] = "  "
    selected = [{**stories[0], "news_items": items}]
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=selected)
    endpoint = {
        "name": "Classification",
        "base_url": "https://llm.test/v1/systemone",
        "api_format": "systemone",
        "model": "classifier",
        "api_key": "classification-key",
        "timeout": 45,
    }
    scores = {category: 0.0 for category in CLASSIFICATION_CATEGORIES}
    scores.update({"security incident": 0.4, "general news": 0.6})
    state = {}
    parameters = {"llm_endpoint": endpoint, "_llm_batch_state": state, "CLASSIFICATION_THRESHOLD": 0.99}
    with patch.object(DecisionsClient, "create_decision", autospec=True) as provider:
        provider.return_value = {"category": scores}
        result = bots.CyberSecClassifierBot().execute(parameters)
        assert provider.await_count == 3
        client = provider.call_args.args[0]
        assert (client.url, client.model, client.api_key, client.timeout) == (endpoint["base_url"], "classifier", "classification-key", 45)
        assert bots.CyberSecClassifierBot().execute(parameters) == result
        assert provider.await_count == 3
    assert result["message"] == "Classified 3 news items"
    assert result["changes"]["story_attributes"] == {selected[0]["id"]: [{"key": "classification", "value": "general news"}]}
    for item in items[:-1]:
        attributes = {attr["key"]: attr["value"] for attr in result["changes"]["item_attributes"][item["id"]]}
        assert attributes["classification"] == "general news"
        assert json.loads(attributes["classification_scores"]) == scores
        assert "cybersecurity_bot" not in attributes


@pytest.mark.parametrize("batch", [False, True])
def test_sentiment_analysis_bot(stories, requests_mock, mock_job, monkeypatch, batch):
    endpoint = {"name": "Sentiment", "base_url": "https://llm.test/v1", "model": "test-model"}
    mock_job.meta = {}
    monkeypatch.setattr("worker.bots.bot_tasks.get_current_job", lambda: mock_job)
    stories = [{**story, "revision": index} for index, story in enumerate(stories)]
    story_get_mock = requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=stories)
    if batch:
        endpoint["processing_mode"] = "openrouter_batch"
    config = requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/bots/sentiment",
        json={"id": "sentiment", "type": "sentiment_analysis_bot", "parameters": {}, "llm_endpoint": endpoint},
    )
    submission = requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"status": "SUCCESS"})
    items = [item for story in stories for item in story["news_items"] if item["content"].strip()]
    outputs = [{"output_text": json.dumps({"sentiment": {"label": "neutral", "score": index / 100}})} for index in range(len(items))]
    expected_scores = {item["id"]: str(index / 100) for index, item in enumerate(items)}
    if batch:
        submitted = requests_mock.post(f"{endpoint['base_url']}/batches", json={"id": "batch_items"}, status_code=202)
        assert isinstance(bot_task("sentiment"), Retry)
        assert submission.call_count == 0
        requests = submitted.last_request.json()["requests"]
        assert len(requests) == len(items)
        assert len({request["custom_id"] for request in requests}) == len(items)
        assert [request["body"]["input"][1]["content"] for request in requests] == [item["content"] for item in items]
        requests_mock.get(
            f"{endpoint['base_url']}/batches/batch_items",
            json={
                "status": "completed",
                "results": [
                    {"custom_id": request["custom_id"], "response": {"status_code": 200, "body": outputs[int(request["custom_id"])]}}
                    for request in reversed(requests)
                ],
            },
        )
        mock_job.meta = json.loads(json.dumps(mock_job.meta))
        result = bot_task("sentiment")
        assert submitted.call_count == 1
    else:
        with patch.object(LLMClient, "create_response", autospec=True) as provider:
            provider.side_effect = outputs
            result = bot_task("sentiment")
            assert provider.await_count == len(items)
            assert [call.args[2] for call in provider.call_args_list] == [item["content"] for item in items]
    assert story_get_mock.call_count == config.call_count == submission.call_count == 1
    assert result["message"] == "Sentiment analysis complete"
    data = submission.last_request.json()["result"]["data"]
    assert data["story_revisions"] == {story["id"]: story["revision"] for story in stories}
    assert data["bot_stages"] == [
        {"bot_id": "sentiment", "bot_type": "SENTIMENT_ANALYSIS_BOT", "story_ids": list(data["story_revisions"]), "result": data["result"]}
    ]
    assert "llm_batch" not in mock_job.meta
    assert len(result["changes"]["item_attributes"]) == len(expected_scores)
    for item_id, changes in result["changes"]["item_attributes"].items():
        attributes = {attr["key"]: attr["value"] for attr in changes}
        assert attributes == {"sentiment_category": "neutral", "sentiment_score": expected_scores[item_id]}
