import json
from unittest.mock import patch

import pytest
from llm_bot.client import LLMClient
from llm_bot.config import Config as LLMConfig

from worker.bot_api import BotServiceUnavailableError
from worker.bots.base_bot import BaseBot
from worker.bots.tagging_content import _news_item_content_for_tagging
from worker.config import Config


pytestmark = pytest.mark.usefixtures("set_transformers_offline")


def test_initalize_bots():
    from worker import bots

    bots.AnalystBot()
    bots.IOCBot()
    bots.GroupingBot()
    bots.NLPBot()
    bots.TaggingBot()
    bots.SummaryBot()
    bots.WordlistBot()


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


@pytest.mark.parametrize(
    "summary,tags,timeout",
    [("Short summary", {"security": {"name": "security", "tag_type": "misc"}}, 17), (None, {}, None)],
)
def test_story_bot_clusters_via_library(stories, requests_mock, monkeypatch, summary, tags, timeout):
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
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/llm-endpoints/clustering", json=endpoint)
    input_stories = [{**story, "summary": summary, "tags": tags} for story in stories[:2]]
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=input_stories)
    grouping = requests_mock.put(f"{Config.TARANIS_CORE_URL}/bots/stories/group-multiple", json={"message": "success"})
    parameters = {"BOT_ENDPOINT": "http://unused-bot.test", "BOT_API_KEY": "unused-bot-key", "REQUESTS_TIMEOUT": timeout}

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
            timeout or 120,
        )
        assert json.loads(provider.call_args.args[2]) == {
            "stories": [{"id": i, "tags": {name: tag["tag_type"] for name, tag in tags.items()}, "summary": summary} for i in (1, 2)]
        }
        assert grouping.call_count == 1
        assert grouping.last_request.json() == [[story["id"] for story in input_stories]]

        provider.return_value = {
            "output_text": json.dumps({"cluster_ids": {"event_clusters": [[1], [2]]}, "cluster_reasons": [], "message": "Processed"})
        }
        assert bots.StoryBot().execute(parameters) == {"message": "Processed. No clusters found."}
        assert grouping.call_count == 1

        endpoint["model"] = ""
        endpoint["api_key"] = ""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/llm-endpoints/clustering", json=endpoint)
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


def test_nlp_bot(story_get_mock, ner_bot_mock):
    from worker import bots

    nlp_bot = bots.NLPBot()
    ner_bot_result = nlp_bot.execute()

    assert story_get_mock.call_count == 1
    assert ner_bot_mock.call_count > 1

    assert ner_bot_result
    assert nlp_bot.bot_api.timeout == Config.REQUESTS_TIMEOUT


def test_nlp_bot_uses_requests_timeout_parameter(story_get_mock, ner_bot_mock):
    from worker import bots

    nlp_bot = bots.NLPBot()
    nlp_bot.execute({"REQUESTS_TIMEOUT": 17})

    assert nlp_bot.bot_api.timeout == 17


@pytest.mark.parametrize("multiple_items", [True, False])
def test_summary_bot_uses_library(stories, story_update_mock, story_attribute_update_mock, requests_mock, multiple_items):
    from worker import bots

    story = {**stories[0], "news_items": [stories[0]["news_items"][0]]}
    if multiple_items:
        story["news_items"].append(stories[1]["news_items"][0])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[story])
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/llm-endpoints/summarization",
        json={
            "name": "Summary",
            "base_url": "https://summary.test/v1",
            "model": "summary-model",
            "api_key": "summary-key",
            "timeout": 42,
        },
    )
    with patch.object(LLMClient, "create_response", autospec=True) as provider:
        provider.side_effect = [{"output_text": '{"summary": "Concise summary"}'}, {"output_text": '{"title": "Generated title"}'}]
        assert bots.SummaryBot().execute() == {"message": "Summarized 1 stories"}
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


def test_cybersec_class_bot(stories, story_get_mock, news_item_attribute_update_mock, story_attribute_update_mock, cybersec_classifier_mock):
    from worker import bots

    def extract_attributes(request_json):
        if isinstance(request_json, dict):
            return request_json.get("attributes", [])
        return request_json

    num_stories = len(stories)
    num_news_items = sum(len(story.get("news_items", [])) for story in stories)

    # setup classifier mock
    cybersec_classifier_mock.post(
        f"{Config.CYBERSEC_CLASSIFIER_API_ENDPOINT}/",
        json={"cybersecurity": 0.6, "non-cybersecurity": 0.05},
    )

    # threshold 0.65 -> all news items classified as no
    cybersec_class_bot = bots.CyberSecClassifierBot()
    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.65
    result_msg = cybersec_class_bot.execute()
    assert result_msg == {"message": f"Classified {num_news_items} news items"}
    assert story_get_mock.call_count == 1
    assert news_item_attribute_update_mock.call_count == num_news_items
    assert story_attribute_update_mock.call_count == num_stories

    request_json_list = [req.json() for req in story_attribute_update_mock.request_history if req.method == "PATCH"][:num_stories]
    cybersec_status_list = [
        d["value"] for attributes_list in request_json_list for d in extract_attributes(attributes_list) if d["key"] == "cybersecurity"
    ]
    assert set(cybersec_status_list) == {"no"}

    # threshold 0.5 -> all news items classified as yes
    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.5
    _ = cybersec_class_bot.execute()
    request_json_list = [req.json() for req in story_attribute_update_mock.request_history if req.method == "PATCH"][
        num_stories : 2 * num_stories
    ]
    cybersec_status_list = [
        d["value"] for attributes_list in request_json_list for d in extract_attributes(attributes_list) if d["key"] == "cybersecurity"
    ]
    assert set(cybersec_status_list) == {"yes"}

    # bot API not reachable -> service failure is propagated
    cybersec_classifier_mock.post(
        f"{Config.CYBERSEC_CLASSIFIER_API_ENDPOINT}/",
        json={"error": f"{Config.CYBERSEC_CLASSIFIER_API_ENDPOINT} not reachable"},
        status_code=404,
    )
    with pytest.raises(BotServiceUnavailableError, match="Bot service is unavailable"):
        cybersec_class_bot.execute()


def test_sentiment_analysis_bot_accepts_flat_response_and_normalizes_label(
    stories,
    story_get_mock,
    news_item_attribute_update_mock,
    requests_mock,
):
    from worker import bots

    requests_mock.post(
        f"{Config.SENTIMENT_ANALYSIS_API_ENDPOINT}/",
        json={"label": "Neutral", "score": 0.49320945143699646},
    )

    sentiment_bot = bots.SentimentAnalysisBot()
    result_msg = sentiment_bot.execute()

    assert result_msg == {"message": "Sentiment analysis complete"}
    assert story_get_mock.call_count == 1
    assert news_item_attribute_update_mock.call_count > 0

    request_json_list = [req.json() for req in news_item_attribute_update_mock.request_history if req.method == "PUT"]
    sentiment_categories = [
        attr["value"] for payload in request_json_list for attr in payload.get("attributes", []) if attr["key"] == "sentiment_category"
    ]
    assert sentiment_categories
    assert set(sentiment_categories) == {"neutral"}
