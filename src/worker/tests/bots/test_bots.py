import pytest

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


def test_summary_bot_uses_configured_summary_and_default_title_endpoints(
    stories,
    requests_mock,
    monkeypatch,
):
    from worker import bots

    story = {**stories[0], "news_items": [stories[0]["news_items"][0], stories[1]["news_items"][0]]}
    story_get_mock = requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[story])
    requests_mock.post("http://summary-bot.test/summary", json={"summary": "Configured summary"})
    requests_mock.post("http://summary-bot.test/title", json={"title": "Configured title"})
    monkeypatch.setattr(Config, "TITLE_API_ENDPOINT", "http://summary-bot.test/title")

    summary_bot = bots.SummaryBot()
    result_msg = summary_bot.execute({"SUMMARY_ENDPOINT": "http://summary-bot.test/summary"})

    assert result_msg["message"] == "Summarized 1 stories"
    assert result_msg["changes"]["story_updates"][story["id"]] == {
        "summary": "Configured summary",
        "title": "Configured title",
    }
    assert result_msg["changes"]["story_attributes"][story["id"]] == [{"key": "SUMMARY_BOT", "value": 1}]
    assert story_get_mock.call_count == 1

    summary_calls = [req for req in requests_mock.request_history if req.url == "http://summary-bot.test/summary"]
    title_calls = [req for req in requests_mock.request_history if req.url == "http://summary-bot.test/title"]
    assert len(summary_calls) == 1
    assert len(title_calls) == 1
    assert all("news_items" in call.json() for call in summary_calls)
    assert all("news_items" in call.json() for call in title_calls)
    assert all(all(set(item.keys()) == {"title", "content"} for item in call.json()["news_items"]) for call in summary_calls + title_calls)
    assert all("/bots/story/" not in call.url for call in requests_mock.request_history)


def test_summary_bot_skips_title_generation_when_title_endpoint_is_unset(
    stories,
    story_get_mock,
    requests_mock,
):
    from worker import bots

    requests_mock.post(
        Config.SUMMARY_API_ENDPOINT,
        json={"summary": "Concise story summary"},
    )

    summary_bot = bots.SummaryBot()
    result_msg = summary_bot.execute()

    assert result_msg["message"] == f"Summarized {len(stories)} stories"
    assert story_get_mock.call_count == 1
    summary_calls = [req for req in requests_mock.request_history if req.url == Config.SUMMARY_API_ENDPOINT]
    assert len(summary_calls) == len(stories)
    assert all("news_items" in call.json() for call in summary_calls)
    assert all(all(set(item.keys()) == {"title", "content"} for item in call.json()["news_items"]) for call in summary_calls)
    assert len(result_msg["changes"]["story_updates"]) == len(stories)
    assert all(set(update) == {"summary"} for update in result_msg["changes"]["story_updates"].values())
    assert all("/bots/story/" not in call.url for call in requests_mock.request_history)


def test_cybersec_class_bot(stories, story_get_mock, cybersec_classifier_mock):
    from worker import bots

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
    assert result_msg["message"] == f"Classified {num_news_items} news items"
    assert story_get_mock.call_count == 1
    assert len(result_msg["changes"]["item_attributes"]) == len({item["id"] for story in stories for item in story["news_items"]})
    assert len(result_msg["changes"]["story_attributes"]) == num_stories
    cybersec_status_list = [
        d["value"]
        for attributes_list in result_msg["changes"]["story_attributes"].values()
        for d in attributes_list
        if d["key"] == "cybersecurity"
    ]
    assert set(cybersec_status_list) == {"no"}

    # threshold 0.5 -> all news items classified as yes
    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.5
    result_msg = cybersec_class_bot.execute()
    cybersec_status_list = [
        d["value"]
        for attributes_list in result_msg["changes"]["story_attributes"].values()
        for d in attributes_list
        if d["key"] == "cybersecurity"
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
    requests_mock,
):
    from worker import bots

    requests_mock.post(
        f"{Config.SENTIMENT_ANALYSIS_API_ENDPOINT}/",
        json={"label": "Neutral", "score": 0.49320945143699646},
    )

    sentiment_bot = bots.SentimentAnalysisBot()
    result_msg = sentiment_bot.execute()

    assert result_msg["message"] == "Sentiment analysis complete"
    assert story_get_mock.call_count == 1
    sentiment_categories = [
        attr["value"]
        for payload in result_msg["changes"]["item_attributes"].values()
        for attr in payload
        if attr["key"] == "sentiment_category"
    ]
    assert sentiment_categories
    assert set(sentiment_categories) == {"neutral"}
    assert all("/bots/news-item/" not in call.url for call in requests_mock.request_history)
