"""Tests for bot task execution and result handling."""

import pytest

import worker.bots
from worker.bots.bot_tasks import _save_task_result, bot_task
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
        """Test that bot_task passes the full result dict to _save_task_result on success."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "ok"})

        # Mock bot execution result - bot returns result WITHOUT bot_type
        bot_execution_result = {
            "result": {"tagged_items": 5, "tags_applied": ["malware", "apt"]},
            "news_items": [{"id": "item1"}, {"id": "item2"}],
        }
        stub_bots._execute_impl = staticmethod(lambda params: bot_execution_result)

        # Execute
        result = bot_task("bot-456", filter={"story_id": "123"})

        # Verify result dict (not message string) is saved
        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "test-job-123"
        assert task_data["task"] == "bot_bot-456"
        assert task_data["status"] == "SUCCESS"
        # Verify the full result dict is passed, not just a message string
        assert isinstance(task_data["result"], dict)
        # Verify bot_type was added by bot_task
        assert "bot_type" in task_data["result"]
        assert task_data["result"]["bot_type"] == "WORDLIST_BOT"
        # Verify bot execution result is included
        assert "result" in task_data["result"]
        assert task_data["result"]["result"] == bot_execution_result["result"]
        assert "news_items" in task_data["result"]

        # Verify return value includes bot_type
        assert result["bot_type"] == "WORDLIST_BOT"
        assert result["result"] == bot_execution_result["result"]

    def test_bot_task_not_found_wraps_error_in_dict(self, current_job, requests_mock):
        """Test that bot_task wraps error messages in dict when bot not found."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-999", status_code=404, json={"error": "not found"})
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "saved"})

        # Execute and expect exception
        with pytest.raises(ValueError, match="Bot with id bot-999 not found"):
            bot_task("bot-999")

        # Verify error is wrapped in dict - called twice due to raise after save
        # First call: specific bot not found error handler
        # Second call: general exception handler
        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 2

        # Check first call (specific error)
        first_call = put_calls[0].json()
        assert first_call["status"] == "FAILURE"
        assert isinstance(first_call["result"], dict)
        assert "error" in first_call["result"]
        assert first_call["result"]["error"] == "Bot with id bot-999 not found"

        # Check second call (exception handler wrapping)
        second_call = put_calls[1].json()
        assert second_call["status"] == "FAILURE"
        assert isinstance(second_call["result"], dict)
        assert "error" in second_call["result"]
        assert "Bot execution failed: Bot with id bot-999 not found" in second_call["result"]["error"]

    def test_bot_task_exception_wraps_error_in_dict(self, current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task wraps exception messages in dict."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "saved"})

        def _raise(*_):
            raise RuntimeError("Bot execution crashed")

        stub_bots._execute_impl = staticmethod(_raise)

        # Execute and expect exception
        with pytest.raises(RuntimeError, match="Bot execution crashed"):
            bot_task("bot-456")

        # Verify error is wrapped in dict
        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert isinstance(task_data["result"], dict)
        assert "error" in task_data["result"]
        assert "Bot execution failed: Bot execution crashed" in task_data["result"]["error"]

    def test_bot_task_without_job_uses_fallback_id(self, no_current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task uses fallback task_id when no RQ job exists."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-789", json=bot_config)
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "saved"})
        stub_bots._execute_impl = staticmethod(lambda params: {"result": "success"})

        # Execute
        bot_task("bot-789")

        # Verify fallback ID is used
        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "bot_bot-789"


class TestSaveTaskResult:
    """Tests for _save_task_result helper function."""

    def test_save_task_result_accepts_dict(self, requests_mock):
        """Test that _save_task_result accepts a dict parameter."""
        result_dict = {
            "bot_type": "IOC_BOT",
            "result": {"iocs_found": 10},
            "news_items": [{"id": "item1"}],
        }

        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "saved"})
        _save_task_result("job-123", "bot_ioc", result_dict, "SUCCESS", CoreApi())

        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1
        assert put_calls[0].json() == {"id": "job-123", "task": "bot_ioc", "result": result_dict, "status": "SUCCESS"}

    def test_save_task_result_formats_payload_correctly(self, requests_mock):
        """Test that _save_task_result formats the API payload correctly."""
        result = {"error": "Something went wrong"}

        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", json={"message": "saved"})
        _save_task_result("job-456", "bot_test", result, "FAILURE", CoreApi())

        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "job-456"
        assert task_data["task"] == "bot_test"
        assert task_data["result"] == result
        assert task_data["status"] == "FAILURE"

    def test_save_task_result_handles_api_failure_gracefully(self, requests_mock, caplog):
        """Test that _save_task_result handles API call failures without raising."""
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", exc=Exception("API connection failed"))

        # Should not raise, just log
        _save_task_result("job-789", "bot_error", {"result": "data"}, "SUCCESS", CoreApi())

        # Verify error was logged
        assert any("Failed to save task result" in record.message for record in caplog.records)

    def test_save_task_result_handles_api_false_response(self, requests_mock):
        """Test that _save_task_result handles False response from API."""
        requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/task-results", status_code=500, json={"error": "nope"})

        # Should not raise, API returned False meaning failure
        _save_task_result("job-999", "bot_fail", {"result": "data"}, "SUCCESS", CoreApi())

        # Verify API was called
        put_calls = [req for req in requests_mock.request_history if req.method == "PUT" and req.url.endswith("/worker/task-results")]
        assert len(put_calls) == 1

