import worker.collectors as collectors
from testdata import news_items

import pytest


@pytest.fixture
def rss_collector():
    return collectors.RSSCollector()


@pytest.fixture
def simple_web_collector():
    return collectors.SimpleWebCollector()


@pytest.fixture
def rt_collector():
    return collectors.RTCollector()


@pytest.fixture
def osint_source_update_mock(requests_mock):
    requests_mock.put("http://taranis/api/worker/osint-sources/1", json={})


@pytest.fixture
def news_item_upload_mock(requests_mock):
    requests_mock.post("http://taranis/api/worker/news-items", json={})


@pytest.fixture
def collectors_mock(osint_source_update_mock, news_item_upload_mock):
    pass


@pytest.fixture
def rt_mock(requests_mock, collectors_mock):
    import rt_testdata

    requests_mock.get(rt_testdata.rt_ticket_search_url, json=rt_testdata.rt_ticket_search_result)
    requests_mock.get(rt_testdata.rt_ticket_url, json=rt_testdata.rt_ticket_1)
    requests_mock.get(rt_testdata.rt_history_url, json=rt_testdata.rt_ticket_history_1)
    requests_mock.get(rt_testdata.rt_transaction_url, json=rt_testdata.rt_ticket_transaction_1)
    requests_mock.get(rt_testdata.rt_attachment_url, json=rt_testdata.rt_ticket_attachment_1)


def test_rt_collector_collect(rt_mock, rt_collector):
    import rt_testdata

    result = rt_collector.collect(rt_testdata.rt_collector_source_data)

    assert result is None


def test_rt_collector_ticket_transaction(rt_mock, rt_collector):
    import rt_testdata

    rt_collector.setup_collector(rt_testdata.rt_collector_source_data)

    result = rt_collector.get_ticket_transaction(1)

    assert result == "1"


def test_simple_web_collector_collect(simple_web_collector):
    from testdata import web_collector_url, web_collector_result_title, web_collector_result_content

    result_item = simple_web_collector.parse_web_content(web_collector_url, "test_source")

    assert result_item["title"] == web_collector_result_title
    # assert result_item["author"] == "John Doe"
    assert result_item["content"].startswith(web_collector_result_content)


@pytest.mark.parametrize("input_news_items", [news_items, news_items[2:], news_items[:: len(news_items) - 1], [news_items[-1]]])
def test_filter_by_word_list_empty_wordlist(rss_collector, input_news_items):
    from testdata import source_empty_wordlist

    emptylist_results = rss_collector.filter_by_word_list(input_news_items, source_empty_wordlist)

    assert emptylist_results == input_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_list(rss_collector, input_news_items, expected_news_items):
    from testdata import source_include_list

    include_list_results = rss_collector.filter_by_word_list(input_news_items, source_include_list)

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
    from testdata import source_exclude_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, source_exclude_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_multiple_list(rss_collector, input_news_items, expected_news_items):
    from testdata import source_include_multiple_list

    include_list_results = rss_collector.filter_by_word_list(input_news_items, source_include_multiple_list)

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
    from testdata import source_exclude_multiple_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, source_exclude_multiple_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_list(rss_collector, input_news_items, expected_news_items):
    from testdata import source_include_list_exclude_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, source_include_list_exclude_list)

    assert include_exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_multiple_lists(rss_collector, input_news_items, expected_news_items):
    from testdata import source_include_multiple_list_exclude_multiple_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, source_include_multiple_list_exclude_multiple_list)

    assert include_exclude_list_results == expected_news_items
