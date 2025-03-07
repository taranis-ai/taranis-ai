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
