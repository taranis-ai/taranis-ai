import pytest
import requests
from worker.tests.testdata import news_items


def test_base_web_collector_conditional_request(base_web_collector_mock, base_web_collector):
    import datetime
    from worker.collectors.base_web_collector import NoChangeError

    response = base_web_collector.send_get_request("https://test.org/200")
    assert response.text == "200 OK"
    assert response.status_code == 200

    with pytest.raises(NoChangeError) as exception:
        response = base_web_collector.send_get_request("https://test.org/no_content")
    assert str(exception.value) == "Not modified"

    with pytest.raises(NoChangeError) as exception:
        response = base_web_collector.send_get_request("https://test.org/304", datetime.datetime(2020, 3, 20, 12))
    assert str(exception.value) == "Not modified"

    with pytest.raises(requests.exceptions.HTTPError) as exception:
        response = base_web_collector.send_get_request("https://test.org/429")
    assert str(exception.value) == "Base Web Collector got Response 429 Too Many Requests. Try decreasing REFRESH_INTERVAL."

    with pytest.raises(requests.exceptions.HTTPError) as exception:
        response = base_web_collector.send_get_request("https://test.org/404")
    assert str(exception.value) == "404 Client Error: None for url: https://test.org/404"


def test_rss_collector(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_rss_collector_get_feed(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data_not_modified
    from worker.tests.testdata import rss_collector_source_data_no_content

    result = rss_collector.collect(rss_collector_source_data_not_modified)
    assert result == "Not modified"

    result = rss_collector.collect(rss_collector_source_data_no_content)
    assert result == "Not modified"


def test_rss_collector_digest_splitting(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["DIGEST_SPLITTING"] = "true"
    rss_collector_source_data["parameters"]["DIGEST_SPLITTING_LIMIT"] = 2
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_rss_collector_with_additional_headers(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234"}'
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None
    assert "Authorization" in rss_collector.headers
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"


def test_rss_collector_initialization_with_additional_headers(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234"}'
    rss_collector.parse_source(rss_collector_source_data)

    assert "Authorization" in rss_collector.headers
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"


@pytest.mark.parametrize(
    "header",
    [
        '{"Authorization: "Bearer Token1234"}',
        '{"key": "value", "invalid"}',
        '{42: "numeric_key"}',
        '{"missing_value":}',
    ],
)
def test_rss_collector_initialization_with_invalid_headers(rss_collector_mock, rss_collector, header):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = header
    with pytest.raises(ValueError, match=f"ADDITIONAL_HEADERS: {header} has to be valid JSON"):
        rss_collector.parse_source(rss_collector_source_data)


def test_rss_collector_with_multiple_additional_headers(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234", "X-Custom-Header": "CustomValue"}'
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None
    assert "Authorization" in rss_collector.headers
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"
    assert "X-Custom-Header" in rss_collector.headers
    assert rss_collector.headers["X-Custom-Header"] == "CustomValue"


def test_rss_collector_with_complex(rss_collector_mock, rss_collector):
    from worker.tests.testdata import rss_collector_source_data_complex

    result = rss_collector.collect(rss_collector_source_data_complex)

    assert result is None
    assert "User-Agent" in rss_collector.headers
    assert rss_collector.headers["User-Agent"] == "Mozilla/5.0"
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"
    assert rss_collector.headers["X-API-KEY"] == "12345"
    assert rss_collector.headers["Cookie"] == "firstcookie=1234; second-cookie=4321"


def test_simple_web_collector_basic(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data

    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_simple_web_collector_xpath(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data, web_collector_source_xpath

    web_collector_source_data["parameters"]["XPATH"] = web_collector_source_xpath
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_simple_web_collector_with_additional_headers(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data

    web_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234"}'
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None
    assert "Authorization" in simple_web_collector.headers
    assert simple_web_collector.headers["Authorization"] == "Bearer Token1234"


def test_simple_web_collector_collect(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_url, web_collector_result_title, web_collector_result_content

    result_item = simple_web_collector.news_item_from_article(web_collector_url)

    assert result_item.title == web_collector_result_title
    # assert result_item.author == "John Doe"
    assert result_item.content.startswith(web_collector_result_content)


def test_simple_web_collector_digest_splitting(simple_web_collector_mock, simple_web_collector):
    from worker.tests.testdata import web_collector_source_data

    web_collector_source_data["parameters"]["XPATH"] = "//*"
    web_collector_source_data["parameters"]["DIGEST_SPLITTING"] = "true"
    web_collector_source_data["parameters"]["DIGEST_SPLITTING_LIMIT"] = 2
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_rt_collector_collect(rt_mock, rt_collector):
    import worker.tests.collectors.rt_testdata as rt_testdata

    result = rt_collector.collect(rt_testdata.rt_collector_source_data)
    assert result is None


def test_rt_collector_no_tickets_error(rt_mock, rt_collector):
    import worker.tests.collectors.rt_testdata as rt_testdata

    # query did not return tickets
    error_msg = f"RT Collector not available {rt_testdata.rt_base_url} with exception: No tickets available for {rt_testdata.rt_base_url}"

    with pytest.raises(RuntimeError) as exception:
        _ = rt_collector.collect(rt_testdata.rt_collector_no_tickets_source_data)
    assert str(exception.value) == error_msg


def test_rt_collector_malformed_json_error(rt_mock, rt_collector):
    import worker.tests.collectors.rt_testdata as rt_testdata

    # query response contains malformed json
    error_msg = f"RT Collector not available {rt_testdata.rt_base_url} with exception: Could not decode result of query as JSON"

    with pytest.raises(RuntimeError) as exception:
        _ = rt_collector.collect(rt_testdata.rt_malformed_json_source_data)
    assert str(exception.value) == error_msg


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
