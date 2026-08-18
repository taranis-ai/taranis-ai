import niquests as requests
import pytest

from tests.testdata import news_items
from worker.config import Config


def test_base_web_collector_conditional_request(base_web_collector_mock, base_web_collector):
    import datetime

    from worker.collectors.base_web_collector import NoChangeError

    response = base_web_collector.send_get_request("https://test.org/200")
    assert response.text == "200 OK"
    assert response.status_code == 200

    response = base_web_collector.send_get_request("https://test.org/no_content")
    assert response.status_code == 200
    assert response.text == ""

    with pytest.raises(NoChangeError) as exception:
        response = base_web_collector.send_get_request("https://test.org/304", datetime.datetime(2020, 3, 20, 12))
    assert str(exception.value) == "https://test.org/304 was not modified"

    with pytest.raises(requests.exceptions.HTTPError) as exception:
        response = base_web_collector.send_get_request("https://test.org/429")
    assert str(exception.value) == "Got Response 429 Too Many Requests. Try decreasing REFRESH_INTERVAL."

    with pytest.raises(requests.exceptions.HTTPError) as exception:
        response = base_web_collector.send_get_request("https://test.org/404")
    assert str(exception.value) == "404 Client Error: None for url: https://test.org/404"


@pytest.mark.parametrize("disable_http3", [False, True])
def test_base_web_collector_http3_config(base_web_collector_mock, base_web_collector, monkeypatch, disable_http3):
    session_class = requests.Session
    session_options = []

    def create_session(**kwargs):
        session_options.append(kwargs)
        return session_class(**kwargs)

    monkeypatch.setattr(Config, "DISABLE_HTTP3", disable_http3)
    monkeypatch.setattr(requests, "Session", create_session)

    base_web_collector.send_get_request("https://test.org/200")

    assert session_options == [{"disable_http3": disable_http3}]


def test_rss_collector(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data

    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_rss_collector_get_feed(rss_collector_mock, rss_collector):
    from tests.testdata import (
        rss_collector_source_data_no_content,
        rss_collector_source_data_not_modified,
        rss_collector_url_not_modified,
    )
    from worker.collectors.base_web_collector import NoChangeError
    from worker.collectors.rss_collector import RSSCollectorError

    with pytest.raises(NoChangeError) as exception:
        rss_collector.collect(rss_collector_source_data_not_modified)
    assert str(exception.value) == f"{rss_collector_url_not_modified} was not modified"

    with pytest.raises(RSSCollectorError, match="No parseable RSS or Atom feed was detected"):
        rss_collector.collect(rss_collector_source_data_no_content)


def test_rss_publish_error_propagates(rss_collector, requests_mock):
    from models.assess import NewsItem

    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", status_code=500, text="failed")

    with pytest.raises(RuntimeError, match="Cannot add news items"):
        rss_collector.publish([NewsItem(osint_source_id="source-1", title="Item")], {"parameters": {}})


def test_primary_http_validator_lifecycle(base_web_collector, requests_mock):
    from worker.collectors.base_web_collector import NoChangeError

    url = "https://example.com/feed"
    validators = {
        "url": url,
        "etag": 'W/"opaque-etag"',
        "last_modified": "Tue, 11 Aug 2026 09:07:03 GMT",
    }
    requests_mock.get(
        url,
        [
            {"text": "feed", "headers": {"ETag": validators["etag"], "Last-Modified": validators["last_modified"]}},
            {"status_code": 304},
            {"text": "manual feed"},
        ],
    )

    base_web_collector.configure_primary_http_resource({}, url, manual=False)
    base_web_collector.send_get_request(url)
    assert base_web_collector.http_validators == validators

    next_collector = type(base_web_collector)()
    next_collector.configure_primary_http_resource({"http_validators": validators}, url, manual=False)
    with pytest.raises(NoChangeError):
        next_collector.send_get_request(url)

    request = requests_mock.request_history[-1]
    assert request.headers["If-None-Match"] == validators["etag"]
    assert request.headers["If-Modified-Since"] == validators["last_modified"]
    assert next_collector.http_validators == validators

    manual_collector = type(base_web_collector)()
    manual_collector.configure_primary_http_resource({"http_validators": validators}, url, manual=True)
    manual_collector.send_get_request(url)

    request = requests_mock.request_history[-1]
    assert "If-None-Match" not in request.headers
    assert "If-Modified-Since" not in request.headers


def test_rss_last_modified_validator_is_sent_to_secondary_resources(rss_collector, requests_mock):
    feed_url = "https://example.com/feed"
    article_url = "https://example.com/article"
    icon_url = "https://example.com/favicon.ico"
    stored_validators = {
        "url": feed_url,
        "etag": 'W/"feed-only"',
        "last_modified": "Tue, 11 Aug 2026 09:07:03 GMT",
    }
    rss_collector.configure_primary_http_resource({"http_validators": stored_validators}, feed_url, manual=False)
    requests_mock.get(article_url, text="<article>article</article>")
    requests_mock.get(icon_url, content=b"icon")

    rss_collector.fetch_article_content(article_url)
    rss_collector._fetch_icon(icon_url)

    for request in requests_mock.request_history:
        assert "If-None-Match" not in request.headers
        assert request.headers["If-Modified-Since"] == stored_validators["last_modified"]


def test_rss_collector_digest_splitting(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["DIGEST_SPLITTING"] = "true"
    rss_collector_source_data["parameters"]["DIGEST_SPLITTING_LIMIT"] = 2
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None


def test_rss_collector_with_additional_headers(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234"}'
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None
    assert "Authorization" in rss_collector.headers
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"


def test_rss_collector_initialization_with_additional_headers(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data

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
    from tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = header
    with pytest.raises(ValueError, match=f"ADDITIONAL_HEADERS: {header} has to be valid JSON"):
        rss_collector.parse_source(rss_collector_source_data)


def test_rss_collector_with_multiple_additional_headers(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data

    rss_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234", "X-Custom-Header": "CustomValue"}'
    result = rss_collector.collect(rss_collector_source_data)

    assert result is None
    assert "Authorization" in rss_collector.headers
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"
    assert "X-Custom-Header" in rss_collector.headers
    assert rss_collector.headers["X-Custom-Header"] == "CustomValue"


def test_rss_collector_with_complex(rss_collector_mock, rss_collector):
    from tests.testdata import rss_collector_source_data_complex

    result = rss_collector.collect(rss_collector_source_data_complex)

    assert result is None
    assert "User-Agent" in rss_collector.headers
    assert rss_collector.headers["User-Agent"] == "Mozilla/5.0"
    assert rss_collector.headers["Authorization"] == "Bearer Token1234"
    assert rss_collector.headers["X-API-KEY"] == "12345"
    assert rss_collector.headers["Cookie"] == "firstcookie=1234; second-cookie=4321"


def test_simple_web_collector_basic(simple_web_collector_mock, simple_web_collector, requests_mock):
    from tests.testdata import web_collector_source_data, web_collector_url

    requests_mock.head(web_collector_url, status_code=405)

    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None
    assert any(request.method == "GET" and request.url == web_collector_url for request in requests_mock.request_history)
    assert all(request.method != "HEAD" for request in requests_mock.request_history)


def test_gather_news_items_uses_playwright(browser_web_collector_mock, browser_web_collector_instance):
    from models.assess import NewsItem

    from tests.testdata import web_collector_result_content, web_collector_result_title

    browser_web_collector_instance.web_url = "https://raw.example.com/testweb.html"
    last_modified = "Tue, 11 Aug 2026 09:07:03 GMT"
    browser_web_collector_instance.configure_primary_http_resource(
        {
            "http_validators": {
                "url": browser_web_collector_instance.web_url,
                "etag": None,
                "last_modified": last_modified,
            }
        },
        browser_web_collector_instance.web_url,
        manual=False,
    )
    browser_web_collector_instance.xpath = ""
    items = browser_web_collector_instance.gather_news_items()
    browser_web_collector_mock.fetch_content_with_js.assert_called_once_with(browser_web_collector_instance.web_url, "")
    browser_web_collector_mock.stop_playwright_if_needed.assert_called_once()
    assert browser_web_collector_mock.request_headers["If-Modified-Since"] == last_modified

    story = items[0]
    assert isinstance(items, list)
    assert len(items) == 1
    assert isinstance(items[0], NewsItem)
    assert story.title == web_collector_result_title
    assert story.content.startswith(web_collector_result_content)
    assert story.link == browser_web_collector_instance.web_url
    assert story.source == browser_web_collector_instance.web_url


def test_simple_web_collector_xpath(simple_web_collector_mock, simple_web_collector):
    from tests.testdata import web_collector_source_data, web_collector_source_xpath

    web_collector_source_data["parameters"]["XPATH"] = web_collector_source_xpath
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_simple_web_collector_with_additional_headers(simple_web_collector_mock, simple_web_collector):
    from tests.testdata import web_collector_source_data

    web_collector_source_data["parameters"]["ADDITIONAL_HEADERS"] = '{"Authorization": "Bearer Token1234"}'
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None
    assert "Authorization" in simple_web_collector.headers
    assert simple_web_collector.headers["Authorization"] == "Bearer Token1234"


def test_simple_web_collector_collect(simple_web_collector_mock, simple_web_collector):
    from tests.testdata import web_collector_result_content, web_collector_result_title, web_collector_url

    result_item = simple_web_collector.news_item_from_article(web_collector_url)

    assert result_item.title == web_collector_result_title
    # assert result_item.author == "John Doe"
    assert result_item.content.startswith(web_collector_result_content)


def test_simple_web_collector_digest_splitting(simple_web_collector_mock, simple_web_collector):
    from tests.testdata import web_collector_source_data

    web_collector_source_data["parameters"]["XPATH"] = "//*"
    web_collector_source_data["parameters"]["DIGEST_SPLITTING"] = "true"
    web_collector_source_data["parameters"]["DIGEST_SPLITTING_LIMIT"] = 2
    result = simple_web_collector.collect(web_collector_source_data)

    assert result is None


def test_rt_collector_collect(rt_mock, rt_collector):
    from tests.collectors import rt_testdata

    result = rt_collector.collect(rt_testdata.rt_collector_source_data)
    assert result is None


def test_rt_collector_no_tickets_error(rt_mock, rt_collector):
    from tests.collectors import rt_testdata

    # query did not return tickets
    error_msg = f"No tickets available for {rt_testdata.rt_base_url}"

    with pytest.raises(RuntimeError) as exception:
        _ = rt_collector.collect(rt_testdata.rt_collector_no_tickets_source_data)
    assert str(exception.value) == error_msg


def test_rt_collector_malformed_json_error(rt_mock, rt_collector):
    import json

    from tests.collectors import rt_testdata

    # query response contains malformed json
    error_msg = "Expecting ':' delimiter: line 1 column 13 (char 12)"

    with pytest.raises((json.decoder.JSONDecodeError, requests.exceptions.JSONDecodeError)) as exception:
        _ = rt_collector.collect(rt_testdata.rt_malformed_json_source_data)
    assert str(exception.value) == error_msg


def test_misp_collector_collect(misp_collector_mock, misp_collector):
    from tests.misp_collector_test_data import source

    result = misp_collector.collect(source)

    assert result is None


@pytest.mark.parametrize("input_news_items", [news_items, news_items[2:], news_items[:: len(news_items) - 1], [news_items[-1]]])
def test_filter_by_word_list_empty_wordlist(rss_collector, input_news_items):
    emptylist_results = rss_collector.filter_by_word_list(input_news_items, [])

    assert emptylist_results == input_news_items


def test_filter_by_word_list_matches_title_content_boundary(rss_collector):
    from models.assess import NewsItem

    item = NewsItem(osint_source_id="source-1", title="foo", content="bar")
    word_lists = [{"usage": ["COLLECTOR_INCLUDELIST"], "entries": [{"value": "bar"}]}]

    assert rss_collector.filter_by_word_list([item], word_lists) == [item]


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_list(rss_collector, input_news_items, expected_news_items):
    from tests.testdata import include_list

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
    from tests.testdata import exclude_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, exclude_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, news_items[:2]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_multiple_list(rss_collector, input_news_items, expected_news_items):
    from tests.testdata import include_multiple_list

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
    from tests.testdata import exclude_multiple_list

    exclude_list_results = rss_collector.filter_by_word_list(input_news_items, exclude_multiple_list)

    assert exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_list(rss_collector, input_news_items, expected_news_items):
    from tests.testdata import include_exclude_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, include_exclude_list)

    assert include_exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "input_news_items,expected_news_items",
    [(news_items, [news_items[0]]), (news_items[2:], []), (news_items[:: len(news_items) - 1], [news_items[0]]), ([news_items[-1]], [])],
)
def test_filter_by_word_list_include_exclude_multiple_lists(rss_collector, input_news_items, expected_news_items):
    from tests.testdata import multiple_include_exclude_list

    include_exclude_list_results = rss_collector.filter_by_word_list(input_news_items, multiple_include_exclude_list)

    assert include_exclude_list_results == expected_news_items


@pytest.mark.parametrize(
    "parameters,expected,expected_timeout",
    [
        # Happy path: all fields present, typical values
        (
            {
                "URL": "https://example.com",
                "API_KEY": "secret",
                "PROXY_SERVER": "http://proxy:8080",
                "ADDITIONAL_HEADERS": '{"User-Agent": "TaranisAI/1.0", "X-Test": "1"}',
                "SSL_CHECK": "true",
                "SHARING_GROUP_ID": "42",
                "ORGANISATION_ID": "org-123",
                "REQUEST_TIMEOUT": 15,
                "DAYS_WITHOUT_CHANGE": "7",
            },
            {
                "url": "https://example.com",
                "api_key": "secret",
                "proxies": {"ftp": "http://proxy:8080", "http": "http://proxy:8080", "https": "http://proxy:8080"},
                "headers": {"User-Agent": "TaranisAI/1.0", "X-Test": "1"},
                "ssl": True,
                "sharing_group_id": 42,
                "org_id": "org-123",
                "days_without_change": "7",
            },
            15,
        ),
        # Happy path: minimal required fields, others default
        (
            {"URL": "u", "API_KEY": "k"},
            {
                "url": "u",
                "api_key": "k",
                "proxies": None,
                "headers": {"User-Agent": "TaranisAI/1.0"},
                "ssl": False,
                "sharing_group_id": None,
                "org_id": "",
                "days_without_change": "",
            },
            Config.REQUESTS_TIMEOUT,
        ),
        # Edge: SHARING_GROUP_ID as int
        (
            {"URL": "u", "API_KEY": "k", "SHARING_GROUP_ID": 99},
            {
                "url": "u",
                "api_key": "k",
                "proxies": None,
                "headers": {"User-Agent": "TaranisAI/1.0"},
                "ssl": False,
                "sharing_group_id": 99,
                "org_id": "",
                "days_without_change": "",
            },
            Config.REQUESTS_TIMEOUT,
        ),
        # Edge: SHARING_GROUP_ID not convertible to int
        (
            {"URL": "u", "API_KEY": "k", "SHARING_GROUP_ID": "not-an-int"},
            {
                "url": "u",
                "api_key": "k",
                "proxies": None,
                "headers": {"User-Agent": "TaranisAI/1.0"},
                "ssl": False,
                "sharing_group_id": None,
                "org_id": "",
                "days_without_change": "",
            },
            Config.REQUESTS_TIMEOUT,
        ),
    ],
    ids=[
        "all_fields_typical",
        "minimal_required",
        "sharing_group_id_int",
        "sharing_group_id_invalid",
    ],
)
def test_parse_parameters_happy_and_edge(parameters, expected, expected_timeout):
    from worker.collectors.misp_collector import MispCollector

    collector = MispCollector()

    collector.parse_parameters(parameters)

    assert collector.url == expected["url"]
    assert collector.api_key == expected["api_key"]
    assert collector.proxies == expected["proxies"]
    assert collector.headers == expected["headers"]
    assert collector.ssl == expected["ssl"]
    assert collector.sharing_group_id == expected["sharing_group_id"]
    assert collector.org_id == expected["org_id"]
    assert collector.days_without_change == expected["days_without_change"]
    assert collector.core_api.timeout == expected_timeout


@pytest.mark.parametrize(
    "parameters,missing_field,expected_message",
    [
        # Error: missing URL
        ({"API_KEY": "k"}, "URL", "Missing URL parameter"),
        # Error: missing API_KEY
        ({"URL": "u"}, "API_KEY", "Missing API_KEY parameter"),
        # Error: both missing
        ({}, "URL", "Missing URL parameter"),
        # Error: URL present but empty string
        ({"URL": "", "API_KEY": "k"}, "URL", "Missing URL parameter"),
        # Error: API_KEY present but empty string
        ({"URL": "u", "API_KEY": ""}, "API_KEY", "Missing API_KEY parameter"),
    ],
    ids=["missing_url", "missing_api_key", "missing_both", "url_empty_string", "api_key_empty_string"],
)
def test_parse_parameters_error_cases(parameters, missing_field, expected_message):
    from worker.collectors.misp_collector import MispCollector

    collector = MispCollector()

    with pytest.raises(ValueError) as excinfo:
        collector.parse_parameters(parameters)
    assert expected_message in str(excinfo.value)
