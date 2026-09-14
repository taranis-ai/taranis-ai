from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from worker.collectors import collector_tasks
from worker.config import Config


@pytest.fixture
def current_job(monkeypatch, mock_job):
    mock_job.meta = {}
    mock_job.save_meta = lambda: None
    monkeypatch.setattr(collector_tasks, "get_current_job", lambda: mock_job)
    return mock_job


def test_collector_task_missing_source_is_recorded_as_failure(current_job, requests_mock):
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/osint-sources/source-missing",
        status_code=404,
        json={"error": "not found"},
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.collector_task("source-missing", False)

    assert result == "Error: Source with id source-missing not found"
    assert current_job.meta["status"] == "FAILURE"
    assert current_job.meta["message"] == result

    put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(put_calls) == 1
    assert put_calls[0].json() == {
        "id": "test-job-123",
        "task": "collector_task",
        "worker_id": "source-missing",
        "worker_type": "collector_task",
        "result": {
            "message": result,
            "reason": "source_not_found",
            "retryable": False,
            "data": {"source_id": "source-missing", "manual": False},
        },
        "status": "FAILURE",
    }


def test_mastodon_failure_result_uses_curated_message_and_recovers(current_job, requests_mock, monkeypatch):
    instance_url = "https://mastodon.example"
    cursor = {"timeline": f"{instance_url}|hashtag|security", "last_status_id": "123"}
    source = {
        "id": "source-1",
        "name": "Mastodon source",
        "type": "mastodon_collector",
        "mastodon_cursor": cursor,
        "parameters": {
            "INSTANCE_URL": instance_url,
            "TIMELINE": "hashtag",
            "HASHTAG": "security",
            "ACCESS_TOKEN": "secret-token-value",
        },
    }
    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    requests_mock.get(
        f"{instance_url}/api/v1/timelines/tag/security",
        [
            {"status_code": 401, "json": {"error": "secret-token-value was rejected"}},
            {"json": []},
        ],
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    with pytest.raises(RuntimeError, match="Mastodon authentication failed or access was denied"):
        collector_tasks.collector_task("source-1", False)

    payload = next(request.json() for request in requests_mock.request_history if request.url.endswith("/tasks"))
    assert payload["status"] == "FAILURE"
    assert payload["result"]["reason"] == "mastodon_authentication_failed"
    assert payload["result"]["message"] == "Mastodon authentication failed or access was denied"
    assert payload["result"]["data"]["mastodon_cursor"] == cursor
    assert "secret-token-value" not in str(payload)

    source["status"] = {"status": payload["status"], "result": payload["result"]}
    result = collector_tasks.collector_task("source-1", False)

    assert result == "No changes: No new Mastodon statuses"
    payloads = [request.json() for request in requests_mock.request_history if request.url.endswith("/tasks")]
    assert payloads[-1]["status"] == "NOT_MODIFIED"
    assert payloads[-1]["result"]["reason"] == "collector_not_modified"
    assert payloads[-1]["result"]["data"]["mastodon_cursor"] == cursor


def test_collector_task_no_change_persists_not_modified_status(current_job, requests_mock, monkeypatch):
    source = {"id": "source-1", "name": "Source 1", "type": "rss_collector", "parameters": {"FEED_URL": "https://example.com/feed"}}

    class FakeCollector:
        name = "RSS Collector"
        http_validators = {
            "url": "https://example.com/feed",
            "etag": 'W/"opaque-etag"',
            "last_modified": "Tue, 11 Aug 2026 09:07:03 GMT",
        }

        def collect(self, source_data, manual):
            raise collector_tasks.NoChangeError("feed was not modified")

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    monkeypatch.setattr(collector_tasks.Collector, "get_collector", lambda self, source_data: FakeCollector())
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.collector_task("source-1", False)

    assert result == "No changes: feed was not modified"
    assert current_job.meta["status"] == "NOT_MODIFIED"
    assert current_job.meta["message"] == result

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json() == {
        "id": "test-job-123",
        "task": "collector_task",
        "worker_id": "source-1",
        "worker_type": "rss_collector",
        "result": {
            "message": result,
            "reason": "collector_not_modified",
            "retryable": False,
            "data": {
                "source_id": "source-1",
                "manual": False,
                "http_validators": FakeCollector.http_validators,
            },
        },
        "status": "NOT_MODIFIED",
    }


def test_empty_rss_feed_result_is_preserved_after_not_modified_response(current_job, requests_mock, monkeypatch):
    feed_url = "https://example.com/feed"
    empty_feed = "<rss version='2.0'><channel><title>Empty</title><link>https://example.com/</link></channel></rss>"
    validators = {
        "url": feed_url,
        "etag": '"empty-feed"',
        "last_modified": "Mon, 17 Aug 2026 10:00:00 GMT",
    }
    source = {
        "id": "source-1",
        "name": "Source 1",
        "type": "rss_collector",
        "parameters": {"FEED_URL": feed_url},
    }

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    requests_mock.get(
        feed_url,
        [
            {
                "text": empty_feed,
                "headers": {"ETag": validators["etag"], "Last-Modified": validators["last_modified"]},
            },
            {"status_code": 304},
        ],
    )
    requests_mock.get("https://example.com/favicon.ico", status_code=404)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.collector_task("source-1", False)
    first_payload = [request.json() for request in requests_mock.request_history if request.method == "POST"][-1]
    source["status"] = {
        "status": first_payload["status"],
        "last_success": "2026-08-18T10:00:00",
        "result": first_payload["result"],
    }
    source["http_validators"] = first_payload["result"]["data"]["http_validators"]

    unchanged_result = collector_tasks.collector_task("source-1", False)

    payloads = [request.json() for request in requests_mock.request_history if request.method == "POST"]
    expected_message = f"RSS feed {feed_url} is valid but currently contains no entries"
    assert result == unchanged_result == expected_message
    assert [payload["status"] for payload in payloads] == ["NOT_MODIFIED", "NOT_MODIFIED"]
    assert [payload["result"]["reason"] for payload in payloads] == ["rss_feed_empty", "rss_feed_empty"]
    assert [payload["result"]["message"] for payload in payloads] == [expected_message, expected_message]
    assert payloads[0]["result"]["data"]["http_validators"] == validators
    assert payloads[1]["result"]["data"]["http_validators"] == validators

    feed_requests = [request for request in requests_mock.request_history if request.method == "GET" and request.url == feed_url]
    assert feed_requests[-1].headers["If-None-Match"] == validators["etag"]


@pytest.mark.parametrize(
    ("publish_message", "result_prefix", "recovered_status", "expected_bot_runs"),
    [
        ("News items added", "'Source 1': News items added", "SUCCESS", 1),
        ("All news items were skipped", "No changes: All news items were skipped", "NOT_MODIFIED", 0),
    ],
)
@pytest.mark.parametrize("skipped_entries", [1, 2])
def test_rss_entry_limit_warning_and_recovery(
    current_job, requests_mock, publish_message, result_prefix, recovered_status, expected_bot_runs, skipped_entries
):
    feed_url = "https://example.com/feed"
    source = {
        "id": "source-1",
        "name": "Source 1",
        "type": "rss_collector",
        "rss_collector_max_entries": 2,
        "parameters": {"FEED_URL": feed_url, "USE_FEED_CONTENT": True},
    }
    entries = "".join(f"<item><title>Item {i}</title><description>Content {i}</description></item>" for i in range(2 + skipped_entries))
    feed = f"<rss version='2.0'><channel><title>Feed</title>{entries}</channel></rss>"
    requests_mock.get(
        feed_url,
        [{"text": feed, "headers": {"ETag": '"feed"'}}, {"status_code": 304}, {"status_code": 304}, {"text": feed}],
    )
    requests_mock.get("https://example.com/favicon.ico", status_code=404)
    source_endpoint = f"{Config.TARANIS_CORE_URL}/worker/osint-sources/source-1"
    requests_mock.get(source_endpoint, json=source)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": publish_message})
    bots = requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/post-collection-bots", json={})
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    warning = (
        "Only 2 entries were considered, in the order provided by the feed (starting at the top). "
        f"{skipped_entries} additional entries were skipped."
    )
    expected_message = f"{result_prefix} {warning}"
    assert collector_tasks.collector_task("source-1") == expected_message
    payload = requests_mock.request_history[-1].json()
    assert payload["status"] == current_job.meta["status"] == "WARNING"
    assert payload["result"]["reason"] == "rss_entry_limit"
    assert payload["result"]["retryable"] is False
    published = next(request.json() for request in requests_mock.request_history if request.url.endswith("/worker/news-items"))
    assert [item["title"] for item in published] == ["Item 0", "Item 1"]
    assert bots.call_count == expected_bot_runs

    source["rss_collector_max_entries"] = 2 + skipped_entries
    for _ in range(2):
        source["status"] = payload
        source["http_validators"] = payload["result"]["data"]["http_validators"]
        requests_mock.get(source_endpoint, json=source)
        assert collector_tasks.collector_task("source-1") == expected_message
        payload = requests_mock.request_history[-1].json()
        assert payload["status"] == "WARNING"

    source["status"] = payload
    requests_mock.get(source_endpoint, json=source)
    collector_tasks.collector_task("source-1", manual=True)
    payload = requests_mock.request_history[-1].json()
    assert payload["status"] == recovered_status
    assert payload["result"]["reason"] != "rss_entry_limit"
    assert warning not in payload["result"]["message"]
    assert bots.call_count == expected_bot_runs * 2

    feed_requests = [request for request in requests_mock.request_history if request.url == feed_url]
    assert feed_requests[1].headers["If-None-Match"] == '"feed"'
    assert feed_requests[2].headers["If-None-Match"] == '"feed"'
    assert "If-None-Match" not in feed_requests[3].headers


def test_rss_parse_failure_cleans_up_persists_failure_and_skips_bots(
    current_job, requests_mock, monkeypatch, rss_collector_mock, rss_collector
):
    from tests.testdata import rss_collector_source_data

    source = deepcopy(rss_collector_source_data)
    source |= {"name": "Source 1", "type": "rss_collector", "rss_collector_max_entries": 1}
    source["parameters"] |= {"BROWSER_MODE": "true", "DIGEST_SPLITTING": "false"}
    playwright_manager = MagicMock()
    monkeypatch.setattr("worker.collectors.rss_collector.PlaywrightManager", lambda *_: playwright_manager)
    monkeypatch.setattr(rss_collector, "parse_feed_entry", MagicMock(side_effect=ValueError("RSS parsing failed")))
    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    monkeypatch.setattr(collector_tasks.Collector, "get_collector", lambda self, source_data: rss_collector)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    with pytest.raises(RuntimeError, match="RSS parsing failed"):
        collector_tasks.collector_task(source["id"], False)

    task_requests = [request for request in requests_mock.request_history if request.url.endswith("/tasks")]
    assert len(task_requests) == 1
    assert task_requests[0].json()["status"] == "FAILURE"
    playwright_manager.stop_playwright_if_needed.assert_called_once_with()
    assert all(not request.url.endswith("/worker/post-collection-bots") for request in requests_mock.request_history)


def test_rss_parse_failure_is_not_reclassified_as_not_modified(current_job, requests_mock, monkeypatch):
    feed_url = "https://example.com/not-a-feed"
    source = {
        "id": "source-1",
        "name": "Invalid RSS source",
        "type": "rss_collector",
        "parameters": {"FEED_URL": feed_url},
    }

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    requests_mock.get(
        feed_url,
        [
            {"text": "<html><body>Not a feed</body></html>", "headers": {"ETag": '"invalid-feed"'}},
            {"status_code": 304},
        ],
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    with pytest.raises(RuntimeError, match="No parseable RSS or Atom feed was detected"):
        collector_tasks.collector_task("source-1", False)

    task_requests = [request for request in requests_mock.request_history if request.method == "POST"]
    first_result = task_requests[-1].json()
    assert first_result["status"] == "FAILURE"
    assert first_result["result"]["data"]["http_validators"]["etag"] == '"invalid-feed"'

    source["status"] = {"last_success": None, "status": "FAILURE", "result": first_result["result"]}
    source["http_validators"] = first_result["result"]["data"]["http_validators"]

    collector_tasks.collector_task("source-1", False)

    feed_requests = [request for request in requests_mock.request_history if request.method == "GET" and request.url == feed_url]
    assert feed_requests[-1].headers["If-None-Match"] == '"invalid-feed"'
    task_requests = [request for request in requests_mock.request_history if request.method == "POST"]
    assert task_requests[-1].json()["status"] == "FAILURE"

    source["parameters"]["USE_FEED_CONTENT"] = True
    requests_mock.get(
        feed_url,
        text="<rss version='2.0'><channel><title>Recovered</title><item><title>Existing item</title></item></channel></rss>",
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "All news items were skipped"})

    collector_tasks.collector_task("source-1", manual=True)

    recovered = requests_mock.request_history[-1].json()
    assert recovered["status"] == "NOT_MODIFIED"
    assert recovered["result"]["reason"] == "collector_not_modified"
    assert recovered["result"]["message"] == "No changes: All news items were skipped"


def test_fetch_single_news_item_accepts_simple_web_source_payload_and_persists_success_result(current_job, requests_mock, monkeypatch):
    captured_parameters = {}

    class FakeSimpleWebCollector:
        name = "Simple Web Collector"

        def preview_collector(self, parameters):
            captured_parameters.update(parameters)
            return [{"title": "Fetched item", "source": parameters["parameters"]["WEB_URL"]}]

    monkeypatch.setattr(collector_tasks.worker.collectors, "SimpleWebCollector", FakeSimpleWebCollector)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.fetch_single_news_item(
        {
            "id": "manual",
            "type": "simple_web_collector",
            "parameters": {"WEB_URL": "https://example.com/story", "XPATH": "//article"},
        }
    )

    assert result == [{"title": "Fetched item", "source": "https://example.com/story"}]
    assert captured_parameters == {
        "id": "manual",
        "type": "simple_web_collector",
        "parameters": {"WEB_URL": "https://example.com/story", "XPATH": "//article"},
    }

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json() == {
        "id": "test-job-123",
        "task": "collector_task",
        "worker_id": "https://example.com/story",
        "worker_type": "simple_web_collector",
        "result": {
            "message": "Fetched news item from https://example.com/story",
            "reason": None,
            "retryable": False,
            "data": [{"title": "Fetched item", "source": "https://example.com/story"}],
        },
        "status": "SUCCESS",
    }


def test_fetch_single_news_item_persists_failure_result(current_job, requests_mock, monkeypatch):
    class FakeSimpleWebCollector:
        name = "Simple Web Collector"

        def preview_collector(self, parameters):
            raise ValueError("connection refused")

    monkeypatch.setattr(collector_tasks.worker.collectors, "SimpleWebCollector", FakeSimpleWebCollector)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    with pytest.raises(RuntimeError, match="connection refused"):
        collector_tasks.fetch_single_news_item(
            {"id": "manual", "type": "simple_web_collector", "parameters": {"WEB_URL": "https://example.com/story"}}
        )

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json()["status"] == "FAILURE"
    assert post_calls[0].json()["result"] == {
        "message": "connection refused",
        "reason": "collection_failed",
        "retryable": False,
        "data": {"source_id": "https://example.com/story"},
    }


def test_collector_preview_persists_with_preview_status(current_job, requests_mock, monkeypatch):
    source = {
        "id": "source-1",
        "name": "Source 1",
        "type": "rss_collector",
        "parameters": {"FEED_URL": "https://example.test/feed"},
    }
    preview_items = [{"title": "Item 1"}, {"title": "Item 2"}]

    class FakeCollector:
        name = "RSS Collector"

        def preview_collector(self, source_data):
            return preview_items

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    monkeypatch.setattr(collector_tasks.Collector, "get_collector", lambda self, source_data: FakeCollector())
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    result = collector_tasks.collector_preview("source-1")

    assert result == preview_items

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json() == {
        "id": "test-job-123",
        "task": "collector_preview",
        "result": {
            "message": "Preview for source source-1 collected",
            "reason": None,
            "retryable": False,
            "data": preview_items,
        },
        "status": "PREVIEW",
    }


def test_collector_preview_persists_failure_on_exception(current_job, requests_mock, monkeypatch):
    source = {
        "id": "source-1",
        "name": "Source 1",
        "type": "rss_collector",
        "parameters": {"FEED_URL": "https://example.test/feed"},
    }

    class FakeCollector:
        name = "RSS Collector"

        def preview_collector(self, source_data):
            raise ValueError("connection refused")

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    monkeypatch.setattr(collector_tasks.Collector, "get_collector", lambda self, source_data: FakeCollector())
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    with pytest.raises(RuntimeError):
        collector_tasks.collector_preview("source-1")

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json()["status"] == "FAILURE"
    assert post_calls[0].json()["task"] == "collector_preview"
    assert post_calls[0].json()["result"] == {
        "message": "connection refused",
        "reason": "preview_failed",
        "retryable": False,
        "data": {"source_id": "source-1"},
    }
