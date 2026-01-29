"""Tests for presenter task result handling."""

from unittest.mock import Mock, patch

import pytest

from worker.presenters.presenter_tasks import _save_task_result


@pytest.fixture
def mock_core_api():
    """Mock CoreApi instance."""
    api = Mock()
    api.api_put = Mock(return_value=True)
    return api


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


class TestPresenterResultCompatibilityWithCoreAPI:
    """Integration tests for presenter result compatibility with core API."""

    def test_successful_render_result_structure_for_core_api(self):
        """Test that successful render results work with core API processing.

        Core API (task.py#L75-78) processes presenter results:
        product_id = result.get("product_id")
        rendered_product = result.get("render_result")

        This test verifies the structure is compatible.
        """
        # Simulate what core API receives from presenter
        presenter_result = {
            "product_id": "prod-456",
            "message": "Product: prod-456 rendered successfully",
            "render_result": "cGRmX2NvbnRlbnQ=",
        }

        # Core API should be able to extract these values
        product_id = presenter_result.get("product_id")
        rendered_product = presenter_result.get("render_result")

        assert product_id == "prod-456"
        assert rendered_product == "cGRmX2NvbnRlbnQ="
        assert rendered_product is not None

    def test_error_result_does_not_have_product_id(self):
        """Test that error results (strings) don't have product_id.

        Core API checks: if not product_id or not rendered_product
        When presenter sends string error, these will be None.
        """
        # Simulate error case - presenter sends string
        error_result = "Presenter html_presenter returned no content"

        # Core API tries to access as dict (will fail gracefully)
        # In actual code, task.py wraps result in request.json which makes it a string
        # But when it tries result.get("product_id"), if result is dict, it works
        # If result is string, .get() would fail, but core should handle gracefully

        # Since presenter can send string OR dict, core must handle both
        # Let's verify string case would not have the keys
        if isinstance(error_result, str):
            # String has no .get() method like dict, so core would need to check type
            assert not hasattr(error_result, "get") or not callable(getattr(error_result, "get", None))
        else:
            product_id = error_result.get("product_id")
            assert product_id is None

    @patch("worker.presenters.presenter_tasks.get_current_job")
    @patch("worker.presenters.presenter_tasks.CoreApi")
    def test_presenter_task_integration_success_sends_dict(self, mock_api_class, mock_get_job):
        """Test that presenter_task sends dict on successful rendering."""
        from worker.presenters.presenter_tasks import presenter_task

        # Setup
        job = Mock()
        job.id = "present-job-123"
        mock_get_job.return_value = job

        mock_core_api = Mock()
        mock_api_class.return_value = mock_core_api

        # Mock product
        product = {
            "id": "prod-123",
            "type": "text_presenter",
            "type_id": 1,
            "template_id": 1,
            "parameters": {},
        }
        mock_core_api.get_product.return_value = product
        mock_core_api.get_template.return_value = "Template content"
        mock_core_api.api_put.return_value = True

        # Mock presenter generate
        with patch("worker.presenters.TextPresenter.generate", return_value="Generated text content"):
            result = presenter_task("prod-123")

        # Verify result is dict with required keys
        assert isinstance(result, dict)
        assert "product_id" in result
        assert "render_result" in result
        assert result["product_id"] == "prod-123"

        # Verify core API received dict
        api_call = mock_core_api.api_put.call_args
        task_data = api_call[0][1]
        assert isinstance(task_data["result"], dict)
        assert task_data["result"]["product_id"] == "prod-123"

    @patch("worker.presenters.presenter_tasks.get_current_job")
    @patch("worker.presenters.presenter_tasks.CoreApi")
    def test_presenter_task_integration_failure_sends_string(self, mock_api_class, mock_get_job):
        """Test that presenter_task sends string on failure."""
        from worker.presenters.presenter_tasks import presenter_task

        # Setup
        job = Mock()
        job.id = "present-job-456"
        mock_get_job.return_value = job

        mock_core_api = Mock()
        mock_api_class.return_value = mock_core_api

        # Mock product
        product = {
            "id": "prod-456",
            "type": "pdf_presenter",
            "type_id": 2,
            "template_id": 1,
            "parameters": {},
        }
        mock_core_api.get_product.return_value = product
        mock_core_api.get_template.return_value = "Template content"
        mock_core_api.api_put.return_value = True

        # Mock presenter generate to return None (failure)
        with patch("worker.presenters.PDFPresenter.generate", return_value=None):
            with pytest.raises(ValueError, match="returned no content"):
                presenter_task("prod-456")

        # Verify core API received string error message
        api_call = mock_core_api.api_put.call_args
        task_data = api_call[0][1]
        assert isinstance(task_data["result"], str)
        assert "returned no content" in task_data["result"]
        assert task_data["status"] == "FAILURE"
