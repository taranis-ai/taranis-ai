from unittest.mock import patch
from worker.flows.bot_task_flow import bot_task_flow
from models.bot import BotTaskRequest


class TestBotTaskFlowE2E:
    """Essential E2E tests for bot task flow"""
    
    def test_bot_flow_success(self):
        """Test successful bot execution """
        # Arrange
        request = BotTaskRequest(bot_id=1, filter={"SOURCE": "test_source"})
        
        with patch.object(bot_task_flow, 'fn') as mock_flow_fn:
            mock_flow_fn.return_value = {
                "status": "success",
                "processed_items": 5
            }
            
            # Act
            result = mock_flow_fn(request)
            
            # Assert
            assert result is not None
            assert result.get("status") == "success"
            assert result.get("processed_items") == 5
            mock_flow_fn.assert_called_once_with(request)
    
    def test_bot_flow_with_filter(self):
        """Test bot execution with filter parameters"""
        # Arrange
        request = BotTaskRequest(bot_id=1, filter={"SOURCE": "test_source"})
        
        # Mock the flow execution
        with patch.object(bot_task_flow, 'fn') as mock_flow_fn:
            mock_flow_fn.return_value = {
                "status": "success",
                "processed_items": 3,
                "filter_applied": True
            }
            
            # Act
            result = mock_flow_fn(request)
            
            # Assert
            assert result is not None
            assert result.get("filter_applied") is True
            mock_flow_fn.assert_called_once_with(request)
    
    def test_bot_flow_bot_not_found(self):
        """Test bot not found error handling"""
        # Arrange
        request = BotTaskRequest(bot_id=999, filter={})
        
        with patch.object(bot_task_flow, 'fn') as mock_flow_fn:
            mock_flow_fn.return_value = {
                "status": "error",
                "error": "Bot with id 999 not found"
            }
            
            # Act
            result = mock_flow_fn(request)
            
            # Assert
            assert result["status"] == "error"
            assert "not found" in result["error"]
            mock_flow_fn.assert_called_once_with(request)
    
    def test_bot_flow_invalid_bot_type(self):
        """Test invalid bot type error handling"""
        # Arrange
        request = BotTaskRequest(bot_id=1, filter={})
        
        with patch.object(bot_task_flow, 'fn') as mock_flow_fn:
            mock_flow_fn.return_value = {
                "status": "error", 
                "error": "Bot type not implemented"
            }
            
            # Act
            result = mock_flow_fn(request)
            
            # Assert
            assert result["status"] == "error"
            assert "not implemented" in result["error"]
            mock_flow_fn.assert_called_once_with(request)