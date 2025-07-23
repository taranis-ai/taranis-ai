import pytest
from worker.flows.collector_task_flow import collector_task_flow
from models.models.collector import CollectorTaskRequest


class TestCollectorTaskFlowE2E:
    """Essential E2E tests for collector task flow"""
    
    def test_collector_flow_success(self, mock_core_api, mock_worker_modules, sample_collector_request):
        """Test successful collection - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_osint_source.return_value = {
            "id": "test_source_1",
            "name": "Test RSS Source", 
            "type": "rss_collector"
        }
        
        # Act
        result = collector_task_flow(sample_collector_request)
        
        # Assert
        assert "Successfully collected source" in result
        assert "Test RSS Source" in result
        mock_core_api.get_osint_source.assert_called_once_with("test_source_1")
        mock_core_api.run_post_collection_bots.assert_called_once_with("test_source_1")
    
    def test_collector_flow_preview_mode(self, mock_core_api, mock_worker_modules):
        """Test preview collection - no post-collection bots"""
        # Arrange
        request = CollectorTaskRequest(source_id="test_source_1", preview=True)
        mock_core_api.get_osint_source.return_value = {
            "id": "test_source_1",
            "type": "rss_collector"
        }
        
        # Act
        result = collector_task_flow(request)
        
        # Assert
        assert result is not None
        mock_core_api.run_post_collection_bots.assert_not_called()
    
    def test_collector_flow_source_not_found(self, mock_core_api, sample_collector_request):
        """Test source not found error"""
        # Arrange
        mock_core_api.get_osint_source.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Source with id .* not found"):
            collector_task_flow(sample_collector_request)
    
    def test_collector_flow_not_modified(self, mock_core_api, mock_worker_modules, sample_collector_request):
        """Test 'Not modified' exception handling"""
        # Arrange
        mock_core_api.get_osint_source.return_value = {
            "id": "test_source_1",
            "name": "Test Source",
            "type": "rss_collector"
        }
        rss_collector_mock = mock_worker_modules["collectors"]["RSSCollector"]
        rss_collector_mock().collect.side_effect = Exception("Not modified")
        
        # Act
        result = collector_task_flow(sample_collector_request)
        
        # Assert
        assert "was not modified" in result