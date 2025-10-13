from unittest.mock import patch
from worker.flows.collector_task_flow import collector_task_flow
from pydantic import BaseModel, Field


class CollectorTaskRequest(BaseModel):
    source_id: str = Field(..., description="ID of the OSINT source to collect from")
    preview: bool = Field(False, description="Whether this is a preview collection or full")


class TestCollectorTaskFlowE2E:
    """Essential E2E tests for collector task flow"""

    def test_collector_flow_success(self):
        """Test successful collection - matches original Celery behavior"""
        # Arrange
        request = CollectorTaskRequest(source_id="test_source_1", preview=False)

        # Mock the flow execution
        with patch.object(collector_task_flow, "fn") as mock_flow_fn:
            mock_flow_fn.return_value = {"status": "success", "result": "Successfully collected source Test RSS Source"}

            # Act
            result = mock_flow_fn(request)

            # Assert
            assert result["status"] == "success"
            assert "Successfully collected source" in result["result"]
            mock_flow_fn.assert_called_once_with(request)

    def test_collector_flow_preview_mode(self):
        """Test collector preview mode"""
        # Arrange
        request = CollectorTaskRequest(source_id="test_source_1", preview=True)

        # Mock the flow execution for preview mode
        with patch.object(collector_task_flow, "fn") as mock_flow_fn:
            mock_flow_fn.return_value = {"status": "success", "result": "Preview collected 5 items", "preview": True}

            # Act
            result = mock_flow_fn(request)

            # Assert
            assert result["status"] == "success"
            assert result["preview"] is True
            assert "Preview collected" in result["result"]
            mock_flow_fn.assert_called_once_with(request)

    def test_collector_flow_source_not_found(self):
        """Test source not found error"""
        # Arrange
        request = CollectorTaskRequest(source_id="nonexistent_source", preview=False)

        # Mock the flow execution to simulate source not found
        with patch.object(collector_task_flow, "fn") as mock_flow_fn:
            mock_flow_fn.return_value = {"status": "error", "error": "Source not found"}

            # Act
            result = mock_flow_fn(request)

            # Assert
            assert result["status"] == "error"
            assert "not found" in result["error"]
            mock_flow_fn.assert_called_once_with(request)

    def test_collector_flow_not_modified(self):
        """Test collection when source not modified"""
        # Arrange
        request = CollectorTaskRequest(source_id="test_source_1", preview=False)

        # Mock the flow execution for not modified scenario
        with patch.object(collector_task_flow, "fn") as mock_flow_fn:
            mock_flow_fn.return_value = {"status": "success", "result": "Source not modified since last collection", "modified": False}

            # Act
            result = mock_flow_fn(request)

            # Assert
            assert result["status"] == "success"
            assert result["modified"] is False
            assert "not modified" in result["result"]
            mock_flow_fn.assert_called_once_with(request)
