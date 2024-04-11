import os
import pytest

import worker.collectors as collectors


def file_loader(filename):
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "r") as f:
            return f.read()
    except OSError as e:
        raise OSError(f"Error while reading file: {e}") from e


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
def web_collector_url_mock(requests_mock):
    from worker.tests.testdata import head_request

    requests_mock.head("https://raw.example.com/testweb.html", json=head_request)
    requests_mock.get("https://raw.example.com/testweb.html", text=file_loader("testweb.html"), headers={"Content-Type": "text/html"})


@pytest.fixture
def collectors_mock(osint_source_update_mock, news_item_upload_mock):
    pass


@pytest.fixture
def rss_collector_mock(requests_mock, collectors_mock):
    from worker.tests.testdata import rss_collector_url, rss_collector_fav_icon_url, rss_collector_targets

    requests_mock.get(rss_collector_targets[0], json={})
    requests_mock.get(rss_collector_targets[1], json={})
    requests_mock.get(rss_collector_targets[2], json={})
    requests_mock.get(rss_collector_fav_icon_url, json={})
    requests_mock.get(rss_collector_url, text=file_loader("test_rss_feed.xml"))


@pytest.fixture
def simple_web_collector_mock(requests_mock, collectors_mock, web_collector_url_mock):
    from worker.tests.testdata import web_collector_fav_icon_url

    requests_mock.get(web_collector_fav_icon_url, json={})


@pytest.fixture
def rt_mock(requests_mock, collectors_mock):
    import worker.tests.collectors.rt_testdata as rt_testdata

    requests_mock.get(rt_testdata.rt_ticket_search_url, json=rt_testdata.rt_ticket_search_result)
    requests_mock.get(rt_testdata.rt_ticket_url, json=rt_testdata.rt_ticket_1)
    requests_mock.get(rt_testdata.rt_history_url, json=rt_testdata.rt_ticket_history_1)
    requests_mock.get(rt_testdata.rt_transaction_url, json=rt_testdata.rt_ticket_transaction_1)
    requests_mock.get(rt_testdata.rt_attachment_url, json=rt_testdata.rt_ticket_attachment_1)
