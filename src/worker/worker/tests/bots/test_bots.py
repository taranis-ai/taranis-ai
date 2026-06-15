from worker.bots.tagging_content import _news_item_content_for_tagging
from worker.config import Config


def test_initalize_bots():
    import worker.bots as bots

    bots.AnalystBot()
    bots.IOCBot()
    bots.GroupingBot()
    bots.NLPBot()
    bots.TaggingBot()
    bots.SummaryBot()
    bots.WordlistBot()


def test_ioc_bot(story_get_mock):
    import worker.bots as bots

    ioc_bot = bots.IOCBot()
    ioc_bot.execute()

    assert story_get_mock.call_count == 1


def test_analyst_bot_returns_meaningful_result_when_no_news_items(monkeypatch):
    import worker.bots as bots

    analyst_bot = bots.AnalystBot()
    monkeypatch.setattr(analyst_bot.core_api, "get_news_items", lambda limit: None)

    result = analyst_bot.execute({"REGULAR_EXPRESSION": "tag", "ATTRIBUTE_NAME": "label"})

    assert result == {"message": "No news items found", "result": {}}


def test_news_item_content_for_tagging_handles_nullable_fields():
    news_item = {"title": None, "review": None, "content": "content"}

    assert _news_item_content_for_tagging(news_item) == "  content"
    assert _news_item_content_for_tagging(news_item, separator="\n") == "\n\ncontent"


def test_nlp_bot(story_get_mock, ner_bot_mock):
    import worker.bots as bots

    nlp_bot = bots.NLPBot()
    ner_bot_result = nlp_bot.execute()

    assert story_get_mock.call_count == 1
    assert ner_bot_mock.call_count > 1

    assert ner_bot_result
    assert nlp_bot.bot_api.timeout == Config.REQUESTS_TIMEOUT


def test_nlp_bot_uses_requests_timeout_parameter(story_get_mock, ner_bot_mock):
    import worker.bots as bots

    nlp_bot = bots.NLPBot()
    nlp_bot.execute({"REQUESTS_TIMEOUT": "17"})

    assert nlp_bot.bot_api.timeout == 17


def test_summary_bot_uses_configured_summary_endpoint_and_optional_title_endpoint(
    stories,
    story_get_mock,
    story_update_mock,
    story_attribute_update_mock,
    requests_mock,
):
    import worker.bots as bots

    requests_mock.post("http://summary-bot.test/summary", json={"summary": "Configured summary"})
    requests_mock.post("http://summary-bot.test/title", json={"title": "Configured title"})

    summary_bot = bots.SummaryBot()
    result_msg = summary_bot.execute(
        {
            "SUMMARY_ENDPOINT": "http://summary-bot.test/summary",
            "TITLE_ENDPOINT": "http://summary-bot.test/title",
        }
    )

    assert result_msg == {"message": f"Summarized {len(stories)} stories"}
    assert story_get_mock.call_count == 1

    summary_calls = [req for req in requests_mock.request_history if req.url == "http://summary-bot.test/summary"]
    title_calls = [req for req in requests_mock.request_history if req.url == "http://summary-bot.test/title"]
    update_calls = [req for req in story_update_mock.request_history if req.method == "PUT"]

    assert len(summary_calls) == len(stories)
    assert not title_calls
    assert len(update_calls) == len(stories)
    assert all("news_items" in call.json() for call in summary_calls)
    assert all("news_items" in call.json() for call in title_calls)
    assert all(all(set(item.keys()) == {"title", "content"} for item in call.json()["news_items"]) for call in summary_calls + title_calls)
    assert all("summary" in call.json() for call in update_calls)
    assert not any("title" in call.json() for call in update_calls)
    assert story_attribute_update_mock.call_count >= len(stories)


def test_summary_bot_skips_title_generation_when_title_endpoint_is_unset(
    stories,
    story_get_mock,
    story_update_mock,
    story_attribute_update_mock,
    requests_mock,
):
    import worker.bots as bots

    requests_mock.post(
        Config.SUMMARY_API_ENDPOINT,
        json={"summary": "Concise story summary"},
    )

    summary_bot = bots.SummaryBot()
    result_msg = summary_bot.execute()

    assert result_msg == {"message": f"Summarized {len(stories)} stories"}
    assert story_get_mock.call_count == 1
    summary_calls = [req for req in requests_mock.request_history if req.url == Config.SUMMARY_API_ENDPOINT]
    assert len(summary_calls) == len(stories)
    assert all("news_items" in call.json() for call in summary_calls)
    assert all(all(set(item.keys()) == {"title", "content"} for item in call.json()["news_items"]) for call in summary_calls)
    assert story_update_mock.call_count == len(stories)
    assert all(list(call.json().keys()) == ["summary"] for call in story_update_mock.request_history if call.method == "PUT")
    assert story_attribute_update_mock.call_count >= len(stories)


def test_cybersec_class_bot(stories, story_get_mock, news_item_attribute_update_mock, story_attribute_update_mock, cybersec_classifier_mock):
    import worker.bots as bots

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

    # bot API not reachable -> all news items classified as none
    cybersec_classifier_mock.post(
        f"{Config.CYBERSEC_CLASSIFIER_API_ENDPOINT}/",
        json={"error": f"{Config.CYBERSEC_CLASSIFIER_API_ENDPOINT} not reachable"},
        status_code=404,
    )
    result_msg = cybersec_class_bot.execute()

    assert result_msg == {"message": "Classified 0 news items"}
    request_json_list = [req.json() for req in story_attribute_update_mock.request_history if req.method == "PATCH"][2 * num_stories :]
    cybersec_status_list = [
        d["value"] for attributes_list in request_json_list for d in extract_attributes(attributes_list) if d["key"] == "cybersecurity"
    ]
    assert set(cybersec_status_list) == {"none"}
