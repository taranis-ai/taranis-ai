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


def test_cybersec_class_bot(stories, story_get_mock, news_item_attribute_update_mock, story_attribute_update_mock, cybersec_classifier_mock):
    import worker.bots as bots

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
    cybersec_status_list = [d["value"] for attributes_list in request_json_list for d in attributes_list if d["key"] == "cybersecurity"]
    assert set(cybersec_status_list) == {"no"}

    # threshold 0.5 -> all news items classified as yes
    Config.CYBERSEC_CLASSIFIER_THRESHOLD = 0.5
    _ = cybersec_class_bot.execute()
    request_json_list = [req.json() for req in story_attribute_update_mock.request_history if req.method == "PATCH"][
        num_stories : 2 * num_stories
    ]
    cybersec_status_list = [d["value"] for attributes_list in request_json_list for d in attributes_list if d["key"] == "cybersecurity"]
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
    cybersec_status_list = [d["value"] for attributes_list in request_json_list for d in attributes_list if d["key"] == "cybersecurity"]
    assert set(cybersec_status_list) == {"none"}
