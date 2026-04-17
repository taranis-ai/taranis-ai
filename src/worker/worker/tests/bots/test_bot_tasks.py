"""Tests for bot task execution and result handling."""

import pytest

import worker.bots
from worker.bots.bot_tasks import bot_task
from worker.config import Config
from worker.core_api import CoreApi


BOT_CLASS_NAMES = [
    "AnalystBot",
    "GroupingBot",
    "TaggingBot",
    "WordlistBot",
    "NLPBot",
    "StoryBot",
    "IOCBot",
    "SummaryBot",
    "SentimentAnalysisBot",
    "CyberSecClassifierBot",
]


@pytest.fixture
def current_job(monkeypatch, mock_job):
    monkeypatch.setattr("worker.bots.bot_tasks.get_current_job", lambda: mock_job)
    return mock_job


@pytest.fixture
def no_current_job(monkeypatch):
    monkeypatch.setattr("worker.bots.bot_tasks.get_current_job", lambda: None)


@pytest.fixture
def bot_config():
    """Sample bot configuration."""
    return {
        "id": "bot-456",
        "type": "wordlist_bot",
        "name": "Test Bot",
        "parameters": {"limit": 5},
    }


@pytest.fixture
def stub_bots(monkeypatch):
    class DummyBot:
        _execute_impl = staticmethod(lambda params: {"result": "ok"})

        def execute(self, params):
            return type(self)._execute_impl(params)

    for class_name in BOT_CLASS_NAMES:
        monkeypatch.setattr(worker.bots, class_name, DummyBot)

    return DummyBot


class TestBotTask:
    """Tests for bot_task function."""

    def test_bot_task_success_passes_result_dict(self, current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task passes the full result dict to CoreApi.save_task_result on success."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "ok"})

        # Mock bot execution result - bot returns a flat result payload
        bot_execution_result = {
            "tagged_items": 5,
            "tags_applied": ["malware", "apt"],
            "news_items": [{"id": "item1"}, {"id": "item2"}],
        }
        stub_bots._execute_impl = staticmethod(lambda params: bot_execution_result)

        # Execute
        result = bot_task("bot-456", filter={"story_id": "123"})

        # Verify result dict (not message string) is saved
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "test-job-123"
        assert task_data["task"] == "bot_bot-456"
        assert task_data["status"] == "SUCCESS"
        assert task_data["worker_id"] == "bot-456"
        assert task_data["worker_type"] == "WORDLIST_BOT"
        # Verify the full result dict is passed, not just a message string
        assert isinstance(task_data["result"], dict)
        assert task_data["result"] == bot_execution_result

        # Verify return value includes worker metadata
        assert result["worker_id"] == "bot-456"
        assert result["worker_type"] == "WORDLIST_BOT"
        assert result["tagged_items"] == 5
        assert result["tags_applied"] == ["malware", "apt"]
        assert result["news_items"] == [{"id": "item1"}, {"id": "item2"}]

    def test_bot_task_not_found_wraps_error_in_dict(self, current_job, requests_mock):
        """Test that bot_task wraps error messages in dict when bot not found."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-999", status_code=404, json={"error": "not found"})
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

        # Execute and expect exception
        with pytest.raises(ValueError, match="Bot with id bot-999 not found"):
            bot_task("bot-999")

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert task_data["worker_id"] == "bot-999"
        assert task_data["worker_type"] == "BOT_TASK"
        assert isinstance(task_data["result"], dict)
        assert "error" in task_data["result"]
        assert task_data["result"]["error"] == "Bot with id bot-999 not found"

    def test_bot_task_exception_wraps_error_in_dict(self, current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task wraps exception messages in dict."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

        def _raise(*_):
            raise RuntimeError("Bot execution crashed")

        stub_bots._execute_impl = staticmethod(_raise)

        # Execute and expect exception
        with pytest.raises(RuntimeError, match="Bot execution crashed"):
            bot_task("bot-456")

        # Verify error is wrapped in dict
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert task_data["worker_id"] == "bot-456"
        assert task_data["worker_type"] == "WORDLIST_BOT"
        assert isinstance(task_data["result"], dict)
        assert "error" in task_data["result"]
        assert "Bot execution failed: Bot execution crashed" in task_data["result"]["error"]

    def test_bot_task_without_job_uses_fallback_id(self, no_current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task uses fallback task_id when no RQ job exists."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-789", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        stub_bots._execute_impl = staticmethod(lambda params: {"result": "success"})

        # Execute
        bot_task("bot-789")

        # Verify fallback ID is used
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "bot_bot-789"


class TestSaveTaskResult:
    """Tests for CoreApi.save_task_result helper."""

    def test_save_task_result_accepts_dict(self, requests_mock):
        """Test that save_task_result accepts a dict parameter."""
        result_dict = {
            "iocs_found": 10,
            "news_items": [{"id": "item1"}],
        }

        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        CoreApi().save_task_result("job-123", "bot_ioc", result_dict, "SUCCESS", worker_id="bot-123", worker_type="IOC_BOT")

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        assert put_calls[0].json() == {
            "id": "job-123",
            "task": "bot_ioc",
            "worker_id": "bot-123",
            "worker_type": "IOC_BOT",
            "result": result_dict,
            "status": "SUCCESS",
        }

    def test_save_task_result_formats_payload_correctly(self, requests_mock):
        """Test that save_task_result formats the API payload correctly."""
        result = {"error": "Something went wrong"}

        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        CoreApi().save_task_result("job-456", "bot_test", result, "FAILURE")

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "job-456"
        assert task_data["task"] == "bot_test"
        assert task_data["result"] == result
        assert task_data["status"] == "FAILURE"

    def test_save_task_result_handles_api_failure_gracefully(self, requests_mock, caplog):
        """Test that save_task_result handles API call failures without raising."""
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", exc=Exception("API connection failed"))

        # Should not raise, just log
        CoreApi().save_task_result("job-789", "bot_error", {"result": "data"}, "SUCCESS")

        # Verify error was logged
        assert any("Failed to save task result" in record.message for record in caplog.records)

    def test_save_task_result_handles_api_false_response(self, requests_mock):
        """Test that save_task_result handles False response from API."""
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", status_code=500, json={"error": "nope"})

        # Should not raise, API returned False meaning failure
        CoreApi().save_task_result("job-999", "bot_fail", {"result": "data"}, "SUCCESS")

        # Verify API was called
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
