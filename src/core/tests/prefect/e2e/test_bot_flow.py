import pytest
from worker.flows.bot_task_flow import bot_task_flow
from models.models.bot import BotTaskRequest


class TestBotTaskFlowE2E:
    """Essential E2E tests for bot task flow"""
    
    def test_bot_flow_success(self, mock_core_api, mock_worker_modules, sample_bot_request):
        """Test successful bot execution - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_bot_config.return_value = {
            "id": "test_bot_1",
            "type": "analyst_bot",
            "parameters": {"REGULAR_EXPRESSION": "test.*pattern"}
        }
        
        # Act
        result = bot_task_flow(sample_bot_request)
        
        # Assert
        assert result is not None
        assert result.get("status") == "success"
        mock_core_api.get_bot_config.assert_called_once_with(sample_bot_request.bot_id)
    
    def test_bot_flow_with_filter(self, mock_core_api, mock_worker_modules):
        """Test bot execution with filter parameters"""
        # Arrange
        request = BotTaskRequest(bot_id=1, filter={"SOURCE": "test_source"})
        mock_core_api.get_bot_config.return_value = {
            "type": "analyst_bot",
            "parameters": {"REGULAR_EXPRESSION": "test"}
        }
        
        # Act
        result = bot_task_flow(request)
        
        # Assert
        assert result is not None
        # Verify filter was passed to bot execution
        analyst_bot_mock = mock_worker_modules["bots"]["AnalystBot"]
        called_params = analyst_bot_mock().execute.call_args[0][0]
        assert "filter" in called_params
    
    def test_bot_flow_bot_not_found(self, mock_core_api, sample_bot_request):
        """Test bot not found error"""
        # Arrange
        mock_core_api.get_bot_config.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Bot with id .* not found"):
            bot_task_flow(sample_bot_request)
    
    def test_bot_flow_invalid_bot_type(self, mock_core_api, sample_bot_request):
        """Test invalid bot type error"""
        # Arrange
        mock_core_api.get_bot_config.return_value = {
            "type": "invalid_bot_type",
            "parameters": {"test": "value"}
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Bot type not implemented"):
            bot_task_flow(sample_bot_request)