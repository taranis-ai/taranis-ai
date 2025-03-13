import os
import pytest
import datetime

import worker.collectors as collectors
from worker.config import Config
from worker.collectors.base_web_collector import BaseWebCollector


def file_loader(filename):
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "r") as f:
            return f.read()
    except OSError as e:
        raise OSError(f"Error while reading file: {e}") from e


@pytest.fixture
def base_web_collector():
    collector = BaseWebCollector()
    collector.last_attempted = datetime.datetime(2022, 1, 1)
    yield collector


@pytest.fixture
def rss_collector():
    collector = collectors.RSSCollector()
    collector.osint_source_id = "test_source"
    yield collector


@pytest.fixture
def simple_web_collector():
    collector = collectors.SimpleWebCollector()
    collector.osint_source_id = "test_source"
    yield collector


@pytest.fixture
def rt_collector():
    return collectors.RTCollector()


@pytest.fixture
def osint_source_update_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/osint-sources/1", json={})


@pytest.fixture
def news_item_upload_mock(requests_mock):
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={})


@pytest.fixture
def web_collector_url_mock(requests_mock):
    from worker.tests.testdata import web_collector_url, web_collector_ref_url, head_request

    requests_mock.head(web_collector_url, json=head_request)
    requests_mock.get(web_collector_url, text=file_loader("testweb.html"), headers={"Content-Type": "text/html"})
    requests_mock.get(web_collector_ref_url, text=file_loader("testweb.html"), headers={"Content-Type": "text/html"})


@pytest.fixture
def collectors_mock(osint_source_update_mock, news_item_upload_mock):
    pass


@pytest.fixture
def base_web_collector_mock(requests_mock):
    requests_mock.get("https://test.org/200", text="200 OK", status_code=200)
    requests_mock.get("https://test.org/no_content", text="", status_code=200)
    requests_mock.get("https://test.org/304", text="", status_code=304)
    requests_mock.get("https://test.org/404", status_code=404)
    requests_mock.get("https://test.org/429", status_code=429)


@pytest.fixture
def rss_collector_mock(requests_mock, collectors_mock):
    from worker.tests.testdata import rss_collector_url, rss_collector_fav_icon_url, rss_collector_targets
    from worker.tests.testdata import rss_collector_url_not_modified, rss_collector_url_no_content

    requests_mock.get(rss_collector_targets[0], json={})
    requests_mock.get(rss_collector_targets[1], json={})
    requests_mock.get(rss_collector_targets[2], json={})
    requests_mock.get(rss_collector_fav_icon_url, json={})
    requests_mock.get(rss_collector_url, text=file_loader("test_rss_feed.xml"))
    requests_mock.get(rss_collector_url_not_modified, text="", status_code=304, headers={"Last-Modified": "Sat, 01 Jan 2022 00:00:00 GMT"})
    requests_mock.get(rss_collector_url_no_content, text="", status_code=200)


@pytest.fixture
def simple_web_collector_mock(requests_mock, collectors_mock, web_collector_url_mock):
    from worker.tests.testdata import web_collector_fav_icon_url

    requests_mock.get(web_collector_fav_icon_url, json={})


@pytest.fixture
def rt_mock(requests_mock, collectors_mock):
    import worker.tests.collectors.rt_testdata as rt_testdata

    requests_mock.get(rt_testdata.rt_ticket_search_url, json=rt_testdata.rt_ticket_search_result)
    requests_mock.get(rt_testdata.rt_no_tickets_url, json={"items": []})
    requests_mock.get(rt_testdata.rt_malformed_json_url, content=b'{"items: [{"id": 1, "content": "test"}]}')
    requests_mock.get(rt_testdata.rt_ticket_url, json=rt_testdata.rt_ticket_1)
    requests_mock.get(rt_testdata.rt_ticket_attachments_url, json=rt_testdata.rt_ticket_attachments)
    requests_mock.get(rt_testdata.rt_attachment_1_url, json=rt_testdata.rt_ticket_attachment_1)
    requests_mock.get(rt_testdata.worker_stories_url, json={})
    requests_mock.get(rt_testdata.favicon_url, json={})
