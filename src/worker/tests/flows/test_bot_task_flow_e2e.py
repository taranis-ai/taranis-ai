import sys
import os
from unittest.mock import Mock, patch

# Add models path
sys.path.insert(0, os.path.abspath('../../models'))

from models.bot import BotTaskRequest


class TestBotTaskFlowE2E:
    
    def test_bot_flow_import_and_basic_execution(self):
        """E2E test: Import flow and test basic execution with mocked dependencies"""
        
        # Mock external dependencies that cause import issues
        mock_modules = {
            'ioc_finder': Mock(),
            'core.log': Mock(),
        }
        
        with patch.dict('sys.modules', mock_modules):
            # Configure logger mock
            mock_logger = Mock()
            sys.modules['core.log'].logger = mock_logger
            
            # Mock CoreApi and worker bots
            with patch('worker.core_api.CoreApi') as mock_core_api_class:
                with patch('worker.bots.AnalystBot') as mock_analyst_bot:
                    
                    # Configure CoreApi mock
                    mock_core_api = Mock()
                    mock_core_api_class.return_value = mock_core_api
                    mock_core_api.get_bot_config.return_value = {
                        "id": "test_bot_1",
                        "type": "analyst_bot",
                        "parameters": {"REGULAR_EXPRESSION": "test.*pattern"}
                    }
                    
                    # Configure bot mock
                    mock_bot_instance = Mock()
                    mock_analyst_bot.return_value = mock_bot_instance
                    mock_bot_instance.execute.return_value = {"processed_items": 5}
                    
                    # Import the flow (this should work now)
                    from worker.flows.bot_task_flow import bot_task_flow
                    
                    # Test that we can create a request
                    request = BotTaskRequest(bot_id=1, filter={"SOURCE": "test"})
                    
                    # Execute the real flow with mocked dependencies
                    result = bot_task_flow(request)
                    
                    # Verify the flow was called and returned expected result
                    assert result is not None
                    assert result.get("processed_items") == 5
                    
                    # Verify CoreApi was called correctly
                    mock_core_api.get_bot_config.assert_called_once_with(1)
                    
                    print("✅ E2E test passed: bot flow executed successfully")
