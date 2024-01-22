import worker.collectors as collectors
from testdata import news_items
import pytest


@pytest.fixture
def rss_collector():
    return collectors.RSSCollector()


@pytest.fixture
def simple_web_collector():
    return collectors.SimpleWebCollector()


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
