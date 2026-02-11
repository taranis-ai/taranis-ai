"""Tests for collector task result handling."""

from worker.collectors.collector_tasks import _save_task_result


class TestCollectorSaveTaskResult:
    """Tests for _save_task_result helper in collector tasks."""

    def test_save_task_result_accepts_string(self, mock_core_api):
        """Test that collector _save_task_result accepts a string parameter."""
        result_message = "Collected 10 items from source 'Test Feed'"

        _save_task_result("job-123", "collector_task", result_message, "SUCCESS", mock_core_api)

        mock_core_api.api_put.assert_called_once_with(
            "/worker/task-results",
            {"id": "job-123", "task": "collector_task", "result": result_message, "status": "SUCCESS"},
        )

    def test_save_task_result_handles_no_changes_message(self, mock_core_api):
        """Test that collector handles 'No changes' messages correctly."""
        result_message = "No changes: Feed has not been updated since last collection"

        _save_task_result("job-456", "collector_task", result_message, "SUCCESS", mock_core_api)

        call_args = mock_core_api.api_put.call_args
        task_data = call_args[0][1]
        assert task_data["result"] == result_message
        assert task_data["status"] == "SUCCESS"

    def test_save_task_result_handles_error_message(self, mock_core_api):
        """Test that collector handles error messages correctly."""
        result_message = "Error: Connection timeout"

        _save_task_result("job-789", "collector_task", result_message, "FAILURE", mock_core_api)

        call_args = mock_core_api.api_put.call_args
        task_data = call_args[0][1]
        assert task_data["result"] == result_message
        assert task_data["status"] == "FAILURE"
