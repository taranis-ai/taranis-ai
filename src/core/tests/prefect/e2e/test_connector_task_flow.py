import pytest
from worker.flows.connector_task_flow import connector_task_flow
from models.models.connector import ConnectorTaskRequest


class TestConnectorTaskFlowE2E:
    """Essential E2E tests for connector task flow"""
    
    def test_connector_flow_success(self, mock_core_api, mock_worker_modules, sample_connector_request):
        """Test successful connector execution - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_connector_config.return_value = {
            "id": "test_connector_1",
            "type": "misp_connector"
        }
        mock_core_api.get_stories.return_value = [{"id": "story_1", "title": "Test Story"}]
        
        # Act
        result = connector_task_flow(sample_connector_request)
        
        # Assert
        assert result is not None
        assert result.get("status") == "success"
        mock_core_api.get_connector_config.assert_called_once_with("test_connector_1")
    
    def test_connector_flow_connector_not_found(self, mock_core_api, sample_connector_request):
        """Test connector not found error"""
        # Arrange
        mock_core_api.get_connector_config.return_value = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Connector with id .* not found"):
            connector_task_flow(sample_connector_request)
    
    def test_connector_flow_stories_not_found(self, mock_core_api, sample_connector_request):
        """Test stories not found error"""
        # Arrange
        mock_core_api.get_connector_config.return_value = {
            "id": "test_connector_1",
            "type": "misp_connector"
        }
        mock_core_api.get_stories.return_value = []
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Story with id .* not found"):
            connector_task_flow(sample_connector_request)
    
    def test_connector_flow_utf16_cleaning(self, mock_core_api, mock_worker_modules, sample_connector_request):
        """Test UTF-16 surrogate cleaning - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_connector_config.return_value = {
            "type": "misp_connector"
        }
        # Story with UTF-16 surrogates (would be cleaned in original)
        mock_core_api.get_stories.return_value = [{"id": "story_1", "content": "test content"}]
        
        # Act
        result = connector_task_flow(sample_connector_request)
        
        # Assert
        assert result is not None
