"""Integration tests for task result processing in core API.

These tests verify that the core API can correctly process task results
sent by workers, ensuring data contract compatibility.
"""

from unittest.mock import patch

from core.api.task import handle_task_specific_result


class TestBotTaskResultProcessing:
    """Tests for bot task result processing at task.py#L83."""

    @patch("core.api.task.NewsItemTagService")
    def test_core_api_processes_bot_result_dict_successfully(self, mock_tag_service):
        """Test that core API successfully calls result.get('result') on bot result dict."""
        # Simulate what worker sends for successful bot execution
        result = {
            "bot_type": "WORDLIST_BOT",
            "result": {
                "tagged_items": 5,
                "tags_applied": ["malware", "apt"],
            },
            "news_items": [
                {"id": "item1", "attributes": []},
                {"id": "item2", "attributes": []},
            ],
        }

        # Execute the core API code
        handle_task_specific_result("bot-job-123", result, "SUCCESS", "bot_bot-456")

        # Verify result.get("result") was successfully accessed (line 83)
        # by checking that the bot processing logic executed
        mock_tag_service.set_found_bot_tags.assert_called_once_with(result, change_by_bot=True)
        mock_tag_service.set_bot_execution_attribute.assert_called_once_with(result)

    @patch("core.api.task.NewsItemTagService")
    def test_core_api_handles_bot_result_with_nested_error(self, mock_tag_service):
        """Test that core API correctly handles result.get('result') when nested result has error."""
        # Simulate what worker sends when bot execution fails
        result = {
            "bot_type": "IOC_BOT",
            "result": {
                "error": "Bot execution failed: Connection timeout",
            },
        }

        # Execute the core API code
        with patch("core.api.task.logger") as mock_logger:
            handle_task_specific_result("bot-job-456", result, "FAILURE", "bot_bot-789")

            # Verify result.get("result") was accessed (line 83)
            # and error was logged (line 85)
            mock_logger.error.assert_called_once_with("Bot execution failed: Connection timeout")

        # Verify tag services were NOT called because of error
        mock_tag_service.set_found_bot_tags.assert_not_called()
        mock_tag_service.set_bot_execution_attribute.assert_not_called()

    @patch("core.api.task.NewsItemTagService")
    def test_core_api_handles_nlp_bot_result(self, mock_tag_service):
        """Test that core API processes NLP bot results correctly."""
        result = {
            "bot_type": "NLP_BOT",
            "result": {
                "entities_extracted": 15,
                "entity_types": ["PERSON", "ORG", "LOC"],
            },
            "news_items": [
                {
                    "id": "news1",
                    "attributes": [{"key": "entity", "value": "Acme Corp"}],
                },
            ],
        }

        # Execute
        handle_task_specific_result("bot-job-789", result, "SUCCESS", "bot_nlp-bot")

        # Verify bot_type check works (line 87-88)
        mock_tag_service.set_found_bot_tags.assert_called_once()
        mock_tag_service.set_bot_execution_attribute.assert_called_once()

    @patch("core.api.task.NewsItemTagService")
    def test_core_api_handles_ioc_bot_result(self, mock_tag_service):
        """Test that core API processes IOC bot results correctly."""
        result = {
            "bot_type": "IOC_BOT",
            "result": {
                "iocs_found": 10,
                "ioc_types": ["ip", "domain", "hash"],
            },
            "news_items": [
                {
                    "id": "news2",
                    "attributes": [
                        {"key": "ioc", "value": "192.168.1.1", "type": "ip"},
                    ],
                },
            ],
        }

        # Execute
        handle_task_specific_result("bot-job-999", result, "SUCCESS", "bot_ioc-bot")

        # Verify IOC_BOT is in tagging_bots list and gets processed
        mock_tag_service.set_found_bot_tags.assert_called_once()
        mock_tag_service.set_bot_execution_attribute.assert_called_once()


class TestCollectorTaskResultProcessing:
    """Tests for collector task result processing at task.py#L81."""

    def test_core_api_logs_collector_string_result(self):
        """Test that core API correctly logs collector string results."""
        result = "'RSS Feed': Collected 10 new articles"

        # Execute with logger mock
        with patch("core.api.task.logger") as mock_logger:
            handle_task_specific_result("collector-job-123", result, "SUCCESS", "collect_rss")

            # Verify result string is logged (line 81)
            mock_logger.info.assert_called_once_with(
                "Collector task collector-job-123 completed with result: 'RSS Feed': Collected 10 new articles"
            )

    def test_core_api_handles_collector_no_changes_result(self):
        """Test that core API handles 'No changes' collector results."""
        result = "No changes: Feed has not been updated since last collection"

        with patch("core.api.task.logger") as mock_logger:
            handle_task_specific_result("collector-job-456", result, "SUCCESS", "collect_atom")

            # Verify string result is logged
            assert mock_logger.info.call_count == 1
            call_args = mock_logger.info.call_args[0][0]
            assert "No changes" in call_args


class TestPresenterTaskResultProcessing:
    """Tests for presenter task result processing at task.py#L75-78."""

    @patch("core.api.task.Product")
    def test_core_api_processes_presenter_dict_result(self, mock_product):
        """Test that core API extracts product_id and render_result from presenter dict."""
        result = {
            "product_id": "prod-789",
            "message": "Product: prod-789 rendered successfully",
            "render_result": "YmFzZTY0X2VuY29kZWRfcGRm",
        }

        # Execute
        handle_task_specific_result("presenter-job-123", result, "SUCCESS", "presenter_task")

        # Verify product_id and render_result were extracted (line 75-76)
        mock_product.update_render_for_id.assert_called_once_with("prod-789", "YmFzZTY0X2VuY29kZWRfcGRm")

    @patch("core.api.task.Product")
    def test_core_api_handles_presenter_missing_fields(self, mock_product):
        """Test that core API handles presenter results with missing fields."""
        result = {
            "message": "Product rendered but missing fields",
            # missing product_id and render_result
        }

        with patch("core.api.task.logger") as mock_logger:
            handle_task_specific_result("presenter-job-456", result, "SUCCESS", "presenter_task")

            # Core API logs error when fields are missing (line 77)
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert "not found or no render result" in call_args

        # Verify update was not called
        mock_product.update_render_for_id.assert_not_called()


class TestWorkerResultDataContracts:
    """End-to-end tests verifying data contracts between worker and core."""

    @patch("core.api.task.NewsItemTagService")
    def test_bot_result_dict_structure_matches_core_expectations(self, mock_tag_service):
        """Verify bot worker sends dict structure that core API expects."""
        # This is the exact structure sent by worker/bots/bot_tasks.py
        worker_bot_result = {
            "bot_type": "WORDLIST_BOT",
            "result": {"tagged_items": 3, "wordlists": ["malware", "apt"]},
            "news_items": [
                {"id": "1", "attributes": [{"key": "tag", "value": "malware"}]},
                {"id": "2", "attributes": [{"key": "tag", "value": "apt"}]},
                {"id": "3", "attributes": [{"key": "tag", "value": "malware"}]},
            ],
        }

        # Core API should process this without errors
        # NOTE: task_id must start with "bot" for bot processing (line 83)
        handle_task_specific_result("bot_rq-job-abc123", worker_bot_result, "SUCCESS", "bot_wordlist")

        # Verify core API successfully:
        # 1. Accessed result.get("result") at line 83
        # 2. Checked bot_type at line 87
        # 3. Called tagging service for WORDLIST_BOT at line 89
        mock_tag_service.set_found_bot_tags.assert_called_once_with(worker_bot_result, change_by_bot=True)
        mock_tag_service.set_bot_execution_attribute.assert_called_once()

    @patch("core.api.task.Product")
    def test_presenter_result_dict_structure_matches_core_expectations(self, mock_product):
        """Verify presenter worker sends dict structure that core API expects."""
        # This is the exact structure sent by worker/presenters/presenter_tasks.py
        worker_presenter_result = {
            "product_id": "report-2026-01",
            "message": "Product: report-2026-01 rendered successfully",
            "render_result": "SGVsbG8gV29ybGQh",  # base64("Hello World!")
        }

        # Core API should process this without errors
        handle_task_specific_result("rq-job-def456", worker_presenter_result, "SUCCESS", "presenter_task")

        # Verify core API successfully:
        # 1. Accessed result.get("product_id") at line 75
        # 2. Accessed result.get("render_result") at line 76
        # 3. Updated product with render result at line 78
        mock_product.update_render_for_id.assert_called_once_with("report-2026-01", "SGVsbG8gV29ybGQh")

    def test_collector_result_string_matches_core_expectations(self):
        """Verify collector worker sends string that core API can log."""
        # This is the exact structure sent by worker/collectors/collector_tasks.py
        worker_collector_result = "'Security News RSS': Collected 25 articles, 10 new"

        with patch("core.api.task.logger") as mock_logger:
            # Core API should process this without errors
            handle_task_specific_result("rq-job-ghi789", worker_collector_result, "SUCCESS", "collect_rss")

            # Verify core API successfully logged string result at line 81
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "rq-job-ghi789" in call_args
            assert "Collected 25 articles" in call_args
