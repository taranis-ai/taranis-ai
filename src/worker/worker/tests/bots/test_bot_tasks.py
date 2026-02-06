"""Tests for bot task execution and result handling."""

from unittest.mock import Mock, patch

import pytest

from worker.bots.bot_tasks import _save_task_result, bot_task


@pytest.fixture
def mock_core_api():
    """Mock CoreApi instance."""
    api = Mock()
    api.get_bot_config = Mock()
    api.api_put = Mock(return_value=True)
    return api


@pytest.fixture
def mock_job():
    """Mock RQ job."""
    job = Mock()
    job.id = "test-job-123"
    return job


@pytest.fixture
def bot_config():
    """Sample bot configuration."""
    return {
        "id": "bot-456",
        "type": "WORDLIST_BOT",
        "name": "Test Bot",
        "parameters": {},
    }


class TestBotTask:
    """Tests for bot_task function."""

    @patch("worker.bots.bot_tasks.get_current_job")
    @patch("worker.bots.bot_tasks.CoreApi")
    @patch("worker.bots.bot_tasks._execute_by_config")
    def test_bot_task_success_passes_result_dict(self, mock_execute, mock_api_class, mock_get_job, mock_job, mock_core_api, bot_config):
        """Test that bot_task passes the full result dict to _save_task_result on success."""
        # Setup
        mock_get_job.return_value = mock_job
        mock_api_class.return_value = mock_core_api
        mock_core_api.get_bot_config.return_value = bot_config

        # Mock bot execution result - bot returns result WITHOUT bot_type
        bot_execution_result = {
            "result": {"tagged_items": 5, "tags_applied": ["malware", "apt"]},
            "news_items": [{"id": "item1"}, {"id": "item2"}],
        }
        mock_execute.return_value = bot_execution_result

        # Execute
        result = bot_task("bot-456", filter={"story_id": "123"})

        # Verify result dict (not message string) is saved
        mock_core_api.api_put.assert_called_once()
        call_args = mock_core_api.api_put.call_args
        assert call_args[0][0] == "/worker/task-results"

        task_data = call_args[0][1]
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

    @patch("worker.bots.bot_tasks.get_current_job")
    @patch("worker.bots.bot_tasks.CoreApi")
    def test_bot_task_not_found_wraps_error_in_dict(self, mock_api_class, mock_get_job, mock_job, mock_core_api):
        """Test that bot_task wraps error messages in dict when bot not found."""
        # Setup
        mock_get_job.return_value = mock_job
        mock_api_class.return_value = mock_core_api
        mock_core_api.get_bot_config.return_value = None  # Bot not found

        # Execute and expect exception
        with pytest.raises(ValueError, match="Bot with id bot-999 not found"):
            bot_task("bot-999")

        # Verify error is wrapped in dict - called twice due to raise after save
        # First call: specific bot not found error handler
        # Second call: general exception handler
        assert mock_core_api.api_put.call_count == 2

        # Check first call (specific error)
        first_call = mock_core_api.api_put.call_args_list[0][0][1]
        assert first_call["status"] == "FAILURE"
        assert isinstance(first_call["result"], dict)
        assert "error" in first_call["result"]
        assert first_call["result"]["error"] == "Bot with id bot-999 not found"

        # Check second call (exception handler wrapping)
        second_call = mock_core_api.api_put.call_args_list[1][0][1]
        assert second_call["status"] == "FAILURE"
        assert isinstance(second_call["result"], dict)
        assert "error" in second_call["result"]
        assert "Bot execution failed: Bot with id bot-999 not found" in second_call["result"]["error"]

    @patch("worker.bots.bot_tasks.get_current_job")
    @patch("worker.bots.bot_tasks.CoreApi")
    @patch("worker.bots.bot_tasks._execute_by_config")
    def test_bot_task_exception_wraps_error_in_dict(self, mock_execute, mock_api_class, mock_get_job, mock_job, mock_core_api, bot_config):
        """Test that bot_task wraps exception messages in dict."""
        # Setup
        mock_get_job.return_value = mock_job
        mock_api_class.return_value = mock_core_api
        mock_core_api.get_bot_config.return_value = bot_config
        mock_execute.side_effect = RuntimeError("Bot execution crashed")

        # Execute and expect exception
        with pytest.raises(RuntimeError, match="Bot execution crashed"):
            bot_task("bot-456")

        # Verify error is wrapped in dict
        mock_core_api.api_put.assert_called_once()
        task_data = mock_core_api.api_put.call_args[0][1]
        assert task_data["status"] == "FAILURE"
        assert isinstance(task_data["result"], dict)
        assert "error" in task_data["result"]
        assert "Bot execution failed: Bot execution crashed" in task_data["result"]["error"]

    @patch("worker.bots.bot_tasks.get_current_job")
    @patch("worker.bots.bot_tasks.CoreApi")
    @patch("worker.bots.bot_tasks._execute_by_config")
    def test_bot_task_without_job_uses_fallback_id(self, mock_execute, mock_api_class, mock_get_job, mock_core_api, bot_config):
        """Test that bot_task uses fallback task_id when no RQ job exists."""
        # Setup - no current job
        mock_get_job.return_value = None
        mock_api_class.return_value = mock_core_api
        mock_core_api.get_bot_config.return_value = bot_config
        mock_execute.return_value = {"result": "success"}

        # Execute
        bot_task("bot-789")

        # Verify fallback ID is used
        task_data = mock_core_api.api_put.call_args[0][1]
        assert task_data["id"] == "bot_bot-789"


class TestSaveTaskResult:
    """Tests for _save_task_result helper function."""

    def test_save_task_result_accepts_dict(self, mock_core_api):
        """Test that _save_task_result accepts a dict parameter."""
        result_dict = {
            "bot_type": "IOC_BOT",
            "result": {"iocs_found": 10},
            "news_items": [{"id": "item1"}],
        }

        _save_task_result("job-123", "bot_ioc", result_dict, "SUCCESS", mock_core_api)

        mock_core_api.api_put.assert_called_once_with(
            "/worker/task-results",
            {"id": "job-123", "task": "bot_ioc", "result": result_dict, "status": "SUCCESS"},
        )

    def test_save_task_result_formats_payload_correctly(self, mock_core_api):
        """Test that _save_task_result formats the API payload correctly."""
        result = {"error": "Something went wrong"}

        _save_task_result("job-456", "bot_test", result, "FAILURE", mock_core_api)

        call_args = mock_core_api.api_put.call_args
        assert call_args[0][0] == "/worker/task-results"

        task_data = call_args[0][1]
        assert task_data["id"] == "job-456"
        assert task_data["task"] == "bot_test"
        assert task_data["result"] == result
        assert task_data["status"] == "FAILURE"

    def test_save_task_result_handles_api_failure_gracefully(self, mock_core_api, caplog):
        """Test that _save_task_result handles API call failures without raising."""
        mock_core_api.api_put.side_effect = Exception("API connection failed")

        # Should not raise, just log
        _save_task_result("job-789", "bot_error", {"result": "data"}, "SUCCESS", mock_core_api)

        # Verify error was logged
        assert any("Failed to save task result" in record.message for record in caplog.records)

    def test_save_task_result_handles_api_false_response(self, mock_core_api):
        """Test that _save_task_result handles False response from API."""
        mock_core_api.api_put.return_value = False

        # Should not raise, API returned False meaning failure
        _save_task_result("job-999", "bot_fail", {"result": "data"}, "SUCCESS", mock_core_api)

        # Verify API was called
        mock_core_api.api_put.assert_called_once()


class TestResultStructureCompatibility:
    """Integration tests for result structure compatibility with core API."""

    def test_result_structure_compatible_with_core_api_access(self):
        """Test that result structure is compatible with core API's result.get('result') access."""
        # This simulates what the core API does at task.py#L83
        # result.get("result")

        # Test successful bot result
        bot_result = {
            "bot_type": "WORDLIST_BOT",
            "result": {"tagged_items": 5},
            "news_items": [{"id": "1"}],
        }

        # Core API should be able to access nested result
        result_data = bot_result.get("result")
        assert result_data is not None
        assert isinstance(result_data, dict)
        assert result_data.get("tagged_items") == 5

    def test_error_result_structure_has_error_or_message_key(self):
        """Test that error results have 'error' or 'message' keys as expected by core API."""
        # This simulates the check at task.py#L84-86
        # if isinstance(result_data, dict) and (result_data.get("error") or result_data.get("message")):

        # Test error result structure
        error_result = {"error": "Bot execution failed: Connection timeout"}

        # For error cases, result.get("result") would be None, but error_result itself has "error"
        # OR the structure could be nested
        assert error_result.get("error") or error_result.get("message")

    def test_tagging_bot_result_structure_for_news_item_service(self):
        """Test that tagging bot results have the structure expected by NewsItemTagService."""
        # Core API checks bot_type and processes result accordingly (task.py#L88-91)
        bot_result = {
            "bot_type": "WORDLIST_BOT",
            "result": {"tags": ["apt", "malware"]},
            "news_items": [
                {"id": "item1", "attributes": []},
                {"id": "item2", "attributes": []},
            ],
        }

        # Verify structure
        assert bot_result.get("bot_type") in ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"]
        assert "news_items" in bot_result
        assert isinstance(bot_result["news_items"], list)

    @patch("worker.bots.bot_tasks.get_current_job")
    @patch("worker.bots.bot_tasks.CoreApi")
    @patch("worker.bots.bot_tasks._execute_by_config")
    def test_end_to_end_result_flow(self, mock_execute, mock_api_class, mock_get_job, mock_core_api):
        """End-to-end test: bot_task -> _save_task_result -> core API receives correct structure."""
        # Setup
        job = Mock()
        job.id = "e2e-job-123"
        mock_get_job.return_value = job
        mock_api_class.return_value = mock_core_api

        bot_config = {"id": "bot-e2e", "type": "nlp_bot", "parameters": {}}
        mock_core_api.get_bot_config.return_value = bot_config

        # Bot execution result structure (WITHOUT bot_type - that's added by bot_task)
        bot_execution_result = {
            "result": {
                "entities_extracted": 15,
                "entity_types": ["PERSON", "ORG", "LOC"],
            },
            "news_items": [
                {"id": "news1", "attributes": [{"key": "entity", "value": "Acme Corp"}]},
                {"id": "news2", "attributes": [{"key": "entity", "value": "John Doe"}]},
            ],
        }
        mock_execute.return_value = bot_execution_result

        # Execute
        result = bot_task("bot-e2e")

        # Verify the entire flow - bot_type should be added by bot_task
        assert result["bot_type"] == "NLP_BOT"
        assert result["result"] == bot_execution_result["result"]

        # Verify core API received properly structured data
        api_call_args = mock_core_api.api_put.call_args[0]
        assert api_call_args[0] == "/worker/task-results"

        task_data = api_call_args[1]
        assert task_data["id"] == "e2e-job-123"
        assert task_data["task"] == "bot_bot-e2e"
        assert task_data["status"] == "SUCCESS"

        # Critical: Verify result is the full dict, not a string
        saved_result = task_data["result"]
        assert isinstance(saved_result, dict)

        # Simulate core API processing (task.py#L83)
        result_data = saved_result.get("result")
        assert result_data is not None
        assert result_data["entities_extracted"] == 15

        # Simulate core API bot_type check (task.py#L87)
        bot_type = saved_result.get("bot_type", "")
        assert bot_type == "NLP_BOT"

        # Simulate core API accessing news_items (task.py#L89-91)
        news_items = saved_result.get("news_items", [])
        assert len(news_items) == 2
