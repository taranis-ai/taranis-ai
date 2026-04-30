import pytest
from models.task_submission_meta import build_worker_task_payload

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

    result = collector_tasks.collector_task(build_worker_task_payload("collector_task", "source-missing", fields={"manual": False}))

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
        "result": result,
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

    result = collector_tasks.collector_task(build_worker_task_payload("collector_task", "source-1", fields={"manual": False}))

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
        "result": result,
        "status": "NOT_MODIFIED",
    }


def test_fetch_single_news_item_accepts_simple_web_source_payload(current_job, monkeypatch):
    captured_parameters = {}

    class FakeSimpleWebCollector:
        name = "Simple Web Collector"

        def preview_collector(self, parameters):
            captured_parameters.update(parameters)
            return [{"title": "Fetched item", "content": "Fetched content", "osint_source_id": "manual"}]

    monkeypatch.setattr(collector_tasks.worker.collectors, "SimpleWebCollector", FakeSimpleWebCollector)

    result = collector_tasks.fetch_single_news_item(
        build_worker_task_payload(
            "fetch_single_news_item",
            "https://example.com/story",
            "simple_web_collector",
            {
                "id": "manual",
                "type": "simple_web_collector",
                "parameters": {"WEB_URL": "https://example.com/story", "XPATH": "//article"},
            },
        )
    )

    assert result == [{"title": "Fetched item", "content": "Fetched content", "osint_source_id": "manual"}]
    assert captured_parameters == {
        "id": "manual",
        "type": "simple_web_collector",
        "parameters": {"WEB_URL": "https://example.com/story", "XPATH": "//article"},
    }
