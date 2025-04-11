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


def test_ioc_bot(story_get_mock, tags_update_mock):
    import worker.bots as bots

    ioc_bot = bots.IOCBot()
    ioc_bot.execute()

    assert story_get_mock.call_count == 1
    assert tags_update_mock.call_count == 1

    assert tags_update_mock.last_request.json() == {
        "1": {"CVE-2020-1234": "cves"},
        "2": {"CVE-2021-5678": "cves"},
        "6": {"CVE-2023-7891": "cves"},
        "7": {"CVE-2023-1234": "cves"},
        "8": {"CVE-2023-5678": "cves"},
    }


def test_nlp_bot(story_get_mock, tags_update_mock, ner_bot_mock):
    import worker.bots as bots

    nlp_bot = bots.NLPBot()
    ner_bot_result = nlp_bot.execute()

    assert story_get_mock.call_count == 1
    assert tags_update_mock.call_count == 1
    assert ner_bot_mock.call_count > 1

    assert ner_bot_result


def test_cybersec_class_bot(stories, story_get_mock, news_item_attribute_update_mock, add_or_update_story_mock, cybersec_classifier_mock):
    import worker.bots as bots

    num_stories = len(stories)
    num_news_items = sum(len(story.get("news_items", [])) for story in stories)

    cybersec_class_bot = bots.CyberSecClassifierBot()
    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.65

    result_msg = cybersec_class_bot.execute()
    assert result_msg == {"message": f"Classified {num_news_items} news_items"}
    assert story_get_mock.call_count == 1
    assert news_item_attribute_update_mock.call_count == num_news_items
    assert add_or_update_story_mock.call_count == num_stories

    cybersec_status_list = [req.json()["cybersecurity"] for req in add_or_update_story_mock.request_history if req.method == "POST"][
        :num_stories
    ]
    assert set(cybersec_status_list) == {"no"}

    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.5
    _ = cybersec_class_bot.execute()
    cybersec_status_list = [req.json()["cybersecurity"] for req in add_or_update_story_mock.request_history if req.method == "POST"][
        num_stories:
    ]
    assert set(cybersec_status_list) == {"yes"}
