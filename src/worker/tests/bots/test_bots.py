import json
from unittest.mock import patch

import pytest
from llm_bot.client import LLMClient
from llm_bot.config import Config as LLMConfig

from worker.bots.base_bot import BaseBot
from worker.bots.tagging_content import _news_item_content_for_tagging
from worker.config import Config


pytestmark = pytest.mark.usefixtures("set_transformers_offline")


@pytest.mark.parametrize(
    "parameters",
    [
        {"ITEM_FILTER": "timefrom=2026-07-01T00%3A00%3A00"},
        {"filter": {"timefrom": "2026-07-01T00:00:00"}},
    ],
)
def test_filter_timefrom_is_forwarded_to_story_query(parameters):
    filter_dict = BaseBot().get_filter_dict(parameters)

    assert filter_dict["timefrom"] == "2026-07-01T00:00:00"


def test_ioc_bot(story_get_mock):
    from worker import bots

    ioc_bot = bots.IOCBot()
    ioc_bot.execute()

    assert story_get_mock.call_count == 1


def test_story_bot_clusters_via_library(stories, requests_mock, monkeypatch):
    from worker import bots

    requests_mock.real_http = False
    endpoint = {
        "name": "Clustering",
        "base_url": "https://llm.test/v1",
        "api_key": "provider-key",
        "model": "cluster-model",
        "api_format": "chat_completions",
        "timeout": 120,
    }
    input_stories = [
        {**stories[0], "summary": "Short summary", "tags": {"security": {"name": "security", "tag_type": "misc"}}},
        {**stories[1], "summary": None, "tags": {}},
    ]
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=input_stories)
    grouping = requests_mock.put(f"{Config.TARANIS_CORE_URL}/bots/stories/group-multiple", json={"message": "success"})
    parameters = {"llm_endpoint": endpoint, "REQUESTS_TIMEOUT": 17}

    with patch.object(LLMClient, "create_response", autospec=True) as provider:
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

        assert result == {"message": "Processed"}
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
        assert grouping.call_count == 1
        assert grouping.last_request.json() == [[story["id"] for story in input_stories]]

        provider.return_value = {
            "output_text": json.dumps({"cluster_ids": {"event_clusters": [[1], [2]]}, "cluster_reasons": [], "message": "Processed"})
        }
        assert bots.StoryBot().execute({"llm_endpoint": endpoint}) == {"message": "Processed. No clusters found."}
        assert provider.call_args.args[0].timeout == 120
        assert grouping.call_count == 1

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


def test_nlp_bot(stories, story_get_mock):
    from worker import bots

    endpoint = {"name": "NER", "base_url": "https://llm.test/v1", "timeout": 42}
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.return_value = {"output_text": '{"Microsoft": "ORG"}'}
        result = bots.NLPBot().execute({"llm_endpoint": endpoint, "REQUESTS_TIMEOUT": 17})
        assert result == {item["id"]: {"Microsoft": "ORG"} for story in stories for item in story["news_items"]}
        assert story_get_mock.call_count == 1
        assert provider.await_count == sum(len(story["news_items"]) for story in stories)
        assert provider.call_args.args[0].timeout == 17
        assert provider.call_args.args[2] == _news_item_content_for_tagging(stories[-1]["news_items"][-1], separator="\n")
        assert "Cybersecurity mode is disabled" in provider.call_args.args[1]

        cyber_story = {**stories[-1], "attributes": {"cybersecurity": {"value": "yes"}}}
        with patch.object(bots.NLPBot, "get_stories", return_value=[cyber_story]):
            bots.NLPBot().execute({"llm_endpoint": endpoint})
        assert "Cybersecurity mode is enabled" in provider.call_args.args[1]
        assert provider.call_args.args[0].timeout == 42


@pytest.mark.parametrize("multiple_items", [True, False])
def test_summary_bot_uses_library(stories, story_update_mock, story_attribute_update_mock, requests_mock, multiple_items):
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
        assert bots.SummaryBot().execute({"llm_endpoint": endpoint}) == {"message": "Summarized 1 stories"}
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
        assert story_update_mock.last_request.json() == expected
        assert story_attribute_update_mock.call_count == 1


@pytest.mark.parametrize("threshold, expected", [(0.65, "no"), (0.5, "yes")])
def test_cybersec_class_bot(stories, story_get_mock, news_item_attribute_update_mock, story_attribute_update_mock, threshold, expected):
    from worker import bots

    endpoint = {"name": "Classification", "base_url": "https://llm.test/v1"}
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.return_value = {"output_text": '{"cybersecurity": 0.6, "non-cybersecurity": 0.4}'}
        result = bots.CyberSecClassifierBot().execute({"llm_endpoint": endpoint, "CLASSIFICATION_THRESHOLD": threshold})
    count = sum(len(story["news_items"]) for story in stories)
    assert result == {"message": f"Classified {count} news items"}
    assert provider.await_count == count
    assert news_item_attribute_update_mock.call_count == count
    assert story_attribute_update_mock.call_count == len(stories)
    assert all(
        {attr["key"]: attr["value"] for attr in req.json()["attributes"]}["cybersecurity"] == expected
        for req in story_attribute_update_mock.request_history
    )
    assert all(
        {attr["key"]: attr["value"] for attr in req.json()["attributes"]}["cybersecurity_bot_score"] == "0.6"
        for req in news_item_attribute_update_mock.request_history
    )


def test_sentiment_analysis_bot(story_get_mock, news_item_attribute_update_mock):
    from worker import bots

    endpoint = {"name": "Sentiment", "base_url": "https://llm.test/v1"}
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.return_value = {"output_text": '{"sentiment": {"label": "neutral", "score": 0.49}}'}
        assert bots.SentimentAnalysisBot().execute({"llm_endpoint": endpoint}) == {"message": "Sentiment analysis complete"}
    assert story_get_mock.call_count == 1
    assert news_item_attribute_update_mock.call_count > 0
    for req in news_item_attribute_update_mock.request_history:
        attributes = {attr["key"]: attr["value"] for attr in req.json()["attributes"]}
        assert attributes == {"sentiment_category": "neutral", "sentiment_score": "0.49"}
