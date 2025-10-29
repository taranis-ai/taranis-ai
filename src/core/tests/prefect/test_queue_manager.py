from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config = {"QUEUE_BROKER_HOST": "localhost", "QUEUE_BROKER_USER": "test_user", "QUEUE_BROKER_PASSWORD": "test_pass"}
    return app


@pytest.fixture
def queue_manager(mock_app):
    from core.managers.queue_manager import QueueManager

    qm = QueueManager(mock_app)
    qm.error = ""
    return qm


class TestQueueManager:
    """Core queue manager tests - focusing on Prefect integration"""

    @patch("core.managers.queue_manager.get_client")
    def test_get_queue_status_success(self, mock_get_client, queue_manager):
        """Test successful Prefect connection"""
        # Mock the async context manager
        mock_client = AsyncMock()
        mock_client.read_flow_runs.return_value = []
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_get_client.return_value = mock_context

        result, status_code = queue_manager.get_queue_status()

        assert status_code == 200
        assert result["status"] == "Prefect agent reachable"

    @patch("core.managers.queue_manager.get_client")
    def test_get_queue_status_failure(self, mock_get_client, queue_manager):
        """Test Prefect connection failure"""
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Connection failed")
        mock_get_client.return_value = mock_context

        result, status_code = queue_manager.get_queue_status()

        assert status_code == 500
        assert "error" in result
        assert "Prefect not available" in result["error"]

    @patch("core.managers.queue_manager.get_client")
    def test_ping_workers_success(self, mock_get_client, queue_manager):
        """Test successful worker ping"""
        mock_client = AsyncMock()
        mock_client.read_flow_runs.return_value = [{"id": "run1"}, {"id": "run2"}]
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_get_client.return_value = mock_context

        result = queue_manager.ping_workers()

        # ping_workers returns the flow runs directly on success
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("core.managers.queue_manager.get_client")
    def test_ping_workers_failure(self, mock_get_client, queue_manager):
        """Test worker ping failure"""
        mock_get_client.side_effect = Exception("Connection failed")

        result, status_code = queue_manager.ping_workers()

        assert status_code == 500
        assert "Could not reach prefect" in result["error"]

    def test_error_state_when_not_initialized(self, queue_manager):
        """Test error handling when QueueManager has errors"""
        queue_manager.error = "Could not connect to Prefect"

        result, status_code = queue_manager.get_queued_tasks()

        assert status_code == 500
        assert "QueueManager not initialized" in result["error"]

    @patch("core.managers.queue_manager.get_client")
    def test_get_queued_tasks_success(self, mock_get_client, queue_manager):
        """Test getting queued tasks via Prefect API"""
        mock_client = AsyncMock()
        mock_client.read_flow_runs.return_value = [
            SimpleNamespace(id="1", flow_name="collectors", state_name="Running", created=None),
            SimpleNamespace(id="2", flow_name="bots", state_name="Pending", created=None),
            SimpleNamespace(id="3", flow_name="bots", state_name="Completed", created=None),
        ]
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_get_client.return_value = mock_context

        result, status_code = queue_manager.get_queued_tasks()

        assert status_code == 200
        assert len(result) == 2
        assert {task["state"] for task in result} == {"Running", "Pending"}

    def test_get_task_method_not_supported(self, queue_manager):
        """Test get_task returns not supported in Prefect"""
        result, status_code = queue_manager.get_task("test_id")

        assert status_code == 501
        assert "Method not supported" in result["error"]
