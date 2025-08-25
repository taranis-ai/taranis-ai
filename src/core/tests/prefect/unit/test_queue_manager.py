
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.unit

@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config = {
        'QUEUE_BROKER_HOST': 'localhost',
        'QUEUE_BROKER_USER': 'test_user', 
        'QUEUE_BROKER_PASSWORD': 'test_pass'
    }
    return app

@pytest.fixture
def queue_manager(mock_app):
    from core.managers.queue_manager import QueueManager
    qm = QueueManager(mock_app)
    qm.error = ""  
    return qm

class TestQueueManager:
    """Core queue manager tests - focusing on Prefect integration"""
    
    @patch('prefect.client.orchestration.get_client')
    def test_get_queue_status_success(self, mock_get_client, queue_manager):
        """Test successful Prefect connection"""
        # Mock the async context manager
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.read_flow_runs.return_value = []

        result, status_code = queue_manager.get_queue_status()

        assert status_code == 200
        assert result["status"] == "Prefect agent reachable"

    @patch('prefect.client.orchestration.get_client')
    def test_get_queue_status_failure(self, mock_get_client, queue_manager):
        """Test Prefect connection failure"""
        mock_get_client.side_effect = Exception("Connection failed")

        result, status_code = queue_manager.get_queue_status()

        assert status_code == 500
        assert "error" in result
        assert "Prefect not available" in result["error"]

    @patch('core.managers.queue_manager.get_client')
    def test_ping_workers_success(self, mock_get_client, queue_manager):
        """Test successful worker ping"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.read_flow_runs.return_value = [{"id": "run1"}, {"id": "run2"}]

        result = queue_manager.ping_workers()

        # ping_workers returns the flow runs directly on success
        assert isinstance(result, list)
        assert len(result) == 2

    @patch('core.managers.queue_manager.get_client')
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

    @patch('requests.get')
    def test_get_queued_tasks_success(self, mock_requests, queue_manager):
        """Test getting queued tasks from RabbitMQ"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {"messages": 5, "name": "collectors", "other": "data"},
            {"messages": 2, "name": "bots", "other": "data"}
        ]
        mock_requests.return_value = mock_response

        result, status_code = queue_manager.get_queued_tasks()

        assert status_code == 200
        assert len(result) == 2
        assert result[0]["messages"] == 5
        assert result[0]["name"] == "collectors"

    def test_get_task_method_not_supported(self, queue_manager):
        """Test get_task returns not supported in Prefect"""
        result, status_code = queue_manager.get_task("test_id")
        
        assert status_code == 400
        assert "Method not supported in Prefect" in result["error"]

   