import pytest

from worker.tests.testdata import news_items


def test_rss_collector(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_rss_collector_digest_splitting(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["DIGEST_SPLITTING"] = "true"
    rss_collector_source_data["parameters"]["DIGEST_SPLITTING_LIMIT"] = 2
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_simple_web_collector_basic(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data

    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_simple_web_collector_xpath(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data, web_collector_source_xpath

    web_collector_source_data["parameters"]["XPATH"] = web_collector_source_xpath
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_rt_collector_collect(rt_mock, rt_collector):
    import worker.tests.collectors.rt_testdata as rt_testdata

    result = rt_collector.collect(rt_testdata.rt_collector_source_data)

    assert result is None


def test_rt_collector_ticket_transaction(rt_mock, rt_collector):
    import worker.tests.collectors.rt_testdata as rt_testdata

    rt_collector.setup_collector(rt_testdata.rt_collector_source_data)

    result = rt_collector.get_ticket_transaction(1)

    assert result == "1"


def test_simple_web_collector_collect(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_url, web_collector_result_title, web_collector_result_content

    result_item = simple_web_collector.news_item_from_article(web_collector_url)

    assert result_item["title"] == web_collector_result_title
    # assert result_item["author"] == "John Doe"
    assert result_item["content"].startswith(web_collector_result_content)


@pytest.mark.parametrize("input_news_items", [news_items, news_items[2:], news_items[:: len(news_items) - 1], [news_items[-1]]])
def test_filter_by_word_list_empty_wordlist(rss_collector, input_news_items):
    emptylist_results = rss_collector.filter_by_word_list(input_news_items, [])

    assert emptylist_results == input_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_list(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import include_list

    include_list_results = rss_collector.filter_by_word_list(input_news_items, include_list)

    assert include_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [
        (news_items, news_items[:: len(news_items) - 1]),
        (news_items[2:], [news_items[-1]]),
        (news_items[:: len(news_items) - 1], news_items[:: len(news_items) - 1]),
        ([news_items[-1]], [news_items[-1]]),
    ],
)
def test_filter_by_word_list_exclude_list(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import exclude_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, exclude_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_multiple_list(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import include_multiple_list

    include_list_results = rss_collector.filter_by_word_list(input_news_items, include_multiple_list)

    assert include_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [
        (news_items, news_items[:: len(news_items) - 1]),
        (news_items[2:], [news_items[-1]]),
        (news_items[:: len(news_items) - 1], news_items[:: len(news_items) - 1]),
        ([news_items[-1]], [news_items[-1]]),
    ],
)
def test_filter_by_word_list_exclude_multiple_list(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import exclude_multiple_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, exclude_multiple_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_list(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import include_exclude_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, include_exclude_list)

    assert include_exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_multiple_lists(rss_collector, input_news_items, expected_news_items):
    from worker.tests.testdata import multiple_include_exclude_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, multiple_include_exclude_list)

    assert include_exclude_list_results == expected_news_items
