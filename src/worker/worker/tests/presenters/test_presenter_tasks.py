"""Tests for presenter task result handling."""

import pytest

from worker.presenters.presenter_tasks import _save_task_result


@pytest.fixture
def set_current_job(monkeypatch):
    def _set(job):
        monkeypatch.setattr("worker.presenters.presenter_tasks.get_current_job", lambda: job)

    return _set


@pytest.fixture
def core_api(monkeypatch, mock_core_api):
    monkeypatch.setattr("worker.presenters.presenter_tasks.CoreApi", lambda: mock_core_api)
    return mock_core_api


class TestPresenterSaveTaskResult:
    """Tests for _save_task_result helper in presenter tasks."""

    def test_save_task_result_accepts_dict(self, mock_core_api):
        """Test that presenter _save_task_result accepts a dict for successful renders."""
        result_dict = {
            "product_id": "prod-123",
            "message": "Product: prod-123 rendered successfully",
            "render_result": "YmFzZTY0X2VuY29kZWRfY29udGVudA==",  # base64 encoded content
        }

        _save_task_result("job-123", "presenter_task", result_dict, "SUCCESS", mock_core_api)

        mock_core_api.api_put.assert_called_once_with(
            "/worker/task-results",
            {"id": "job-123", "task": "presenter_task", "result": result_dict, "status": "SUCCESS"},
        )

    def test_save_task_result_accepts_string_for_errors(self, mock_core_api):
        """Test that presenter _save_task_result accepts a string for error messages."""
        error_message = "Presenter pdf_presenter returned no content"

        _save_task_result("job-456", "presenter_task", error_message, "FAILURE", mock_core_api)

        call_args = mock_core_api.api_put.call_args
        task_data = call_args[0][1]
        assert task_data["result"] == error_message
        assert task_data["status"] == "FAILURE"

    def test_save_task_result_formats_payload_correctly_with_dict(self, mock_core_api):
        """Test that presenter formats API payload correctly with dict result."""
        result = {
            "product_id": "prod-789",
            "message": "PDF generated",
            "render_result": "cGRmX2RhdGE=",
        }

        _save_task_result("job-789", "presenter_task", result, "SUCCESS", mock_core_api)

        call_args = mock_core_api.api_put.call_args
        assert call_args[0][0] == "/worker/task-results"

        task_data = call_args[0][1]
        assert task_data["id"] == "job-789"
        assert task_data["task"] == "presenter_task"
        assert task_data["result"] == result
        assert task_data["status"] == "SUCCESS"

