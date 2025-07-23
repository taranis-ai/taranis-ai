import pytest
from worker.flows.publisher_task_flow import publisher_task_flow
from models.models.publisher import PublisherTaskRequest


class TestPublisherTaskFlowE2E:
    """Essential E2E tests for publisher task flow"""
    
    def test_publisher_flow_success(self, mock_core_api, mock_worker_modules, sample_publisher_request):
        """Test successful publishing - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_product.return_value = {
            "id": "test_product_1",
            "title": "Test Product"
        }
        mock_core_api.get_publisher.return_value = {
            "id": "test_publisher_1",
            "type": "email_publisher"
        }
        mock_core_api.get_product_render.return_value = mock_worker_modules  # Mock Product object
        
        # Act
        result = publisher_task_flow(sample_publisher_request)
        
        # Assert
        assert result is not None
        assert result.get("status") == "published"
        mock_core_api.get_product.assert_called_once_with(1)  # Converted to int
        mock_core_api.get_publisher.assert_called_once_with("test_publisher_1")
    
    def test_publisher_flow_product_not_found(self, mock_core_api, sample_publisher_request):
        """Test product not found error"""
        # Arrange
        mock_core_api.get_product.return_value = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Product with id .* not found"):
            publisher_task_flow(sample_publisher_request)
    
    def test_publisher_flow_publisher_not_found(self, mock_core_api, sample_publisher_request):
        """Test publisher not found error"""
        # Arrange
        mock_core_api.get_product.return_value = {"id": "test_product_1"}
        mock_core_api.get_publisher.return_value = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Publisher with id .* not found"):
            publisher_task_flow(sample_publisher_request)
    
    def test_publisher_flow_rendered_product_none(self, mock_core_api, sample_publisher_request):
        """Test rendered product is None error"""
        # Arrange
        mock_core_api.get_product.return_value = {"id": "test_product_1"}
        mock_core_api.get_publisher.return_value = {"type": "email_publisher"}
        mock_core_api.get_product_render.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Rendered product is None"):
            publisher_task_flow(sample_publisher_request)