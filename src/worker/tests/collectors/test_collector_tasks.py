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


def test_collector_task_no_change_persists_not_modified_status(current_job, requests_mock, monkeypatch):
    source = {"id": "source-1", "name": "Source 1", "type": "rss_collector", "parameters": {"FEED_URL": "https://example.com/feed"}}

    class FakeCollector:
        name = "RSS Collector"

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
            "data": {"source_id": "source-1", "manual": False},
        },
        "status": "NOT_MODIFIED",
    }


def test_empty_rss_feed_status_lifecycle(current_job, requests_mock, monkeypatch):
    feed_url = "https://example.com/feed"
    source = {
        "id": "source-1",
        "name": "Source 1",
        "type": "rss_collector",
        "parameters": {"FEED_URL": feed_url},
    }

    monkeypatch.setattr(collector_tasks.Collector, "get_source", lambda self, osint_source_id: source)
    requests_mock.get(
        feed_url,
        text="<rss version='2.0'><channel><title>Empty</title><link>https://example.com/</link></channel></rss>",
    )
    requests_mock.get("https://example.com/favicon.ico", status_code=404)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

    for _ in range(2):
        collector_tasks.collector_task("source-1", False)
        payload = requests_mock.request_history[-1].json()
        source["status"] = {"last_success": None, "result": payload["result"]}

    with pytest.raises(RuntimeError, match="after 3 collection attempts"):
        collector_tasks.collector_task("source-1", False)

    source["status"] = {"last_success": "2026-08-14T10:00:00"}
    collector_tasks.collector_task("source-1", False)

    payloads = [request.json() for request in requests_mock.request_history if request.method == "POST"]
    assert [payload["status"] for payload in payloads] == ["PENDING", "PENDING", "FAILURE", "NOT_MODIFIED"]
    assert "attempt 1 of 3" in payloads[0]["result"]["message"]
    assert "attempt 2 of 3" in payloads[1]["result"]["message"]
    assert "after 3 collection attempts" in payloads[2]["result"]["message"]
    assert "after an earlier successful collection" in payloads[3]["result"]["message"]


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
    source = {"id": "source-1", "name": "Source 1", "type": "rss_collector", "parameters": {}}
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
    source = {"id": "source-1", "name": "Source 1", "type": "rss_collector", "parameters": {}}

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
