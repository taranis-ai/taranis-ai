import pytest
from worker.flows.presenter_task_flow import presenter_task_flow
from models.presenter import PresenterTaskRequest


class TestPresenterTaskFlowE2E:
    """Essential E2E tests for presenter task flow"""
    
    def test_presenter_flow_success(self, mock_core_api, mock_worker_modules, sample_presenter_request):
        """Test successful presentation - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_product.return_value = {
            "id": "test_product_1",
            "title": "Test Product",
            "type": "html_presenter",
            "type_id": "1"
        }
        mock_core_api.get_template.return_value = "<html>{{data.title}}</html>"
        
        # Act
        result = presenter_task_flow(sample_presenter_request)
        
        # Assert
        assert result is not None
        assert result["product_id"] == 1  # Converted to int
        assert result["message"] == "Product: 1 rendered successfully"
        assert "render_result" in result  # Base64 encoded content
    
    def test_presenter_flow_product_not_found(self, mock_core_api, sample_presenter_request):
        """Test product not found error"""
        # Arrange
        mock_core_api.get_product.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Product with id .* not found"):
            presenter_task_flow(sample_presenter_request)
    
    def test_presenter_flow_template_not_found(self, mock_core_api, sample_presenter_request):
        """Test template not found error"""
        # Arrange
        mock_core_api.get_product.return_value = {
            "id": "test_product_1",
            "type": "html_presenter",
            "type_id": "1"
        }
        mock_core_api.get_template.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Template with id .* not found"):
            presenter_task_flow(sample_presenter_request)
    
    def test_presenter_flow_base64_encoding(self, mock_core_api, mock_worker_modules, sample_presenter_request):
        """Test base64 encoding - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_product.return_value = {
            "type": "html_presenter",
            "type_id": "1"
        }
        mock_core_api.get_template.return_value = "<html>test</html>"
        
        html_presenter_mock = mock_worker_modules["presenters"]["HTMLPresenter"]
        html_presenter_mock().generate.return_value = "<html>Generated content</html>"
        
        # Act
        result = presenter_task_flow(sample_presenter_request)
        
        # Assert
        assert "render_result" in result
        # Result should be base64 encoded like original
        import base64
        decoded = base64.b64decode(result["render_result"]).decode("ascii")
        assert "Generated content" in decoded