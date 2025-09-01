import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

current_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(current_dir, '../../../models')
src_dir = os.path.join(current_dir, '../../../')

sys.path.insert(0, os.path.abspath(models_dir))
sys.path.insert(0, os.path.abspath(src_dir))

from models.bot import BotTaskRequest
from models.collector import CollectorTaskRequest 
from models.connector import ConnectorTaskRequest
from models.presenter import PresenterTaskRequest
from models.publisher import PublisherTaskRequest


@pytest.fixture(scope="function")
def mock_core_api():
    """Mock CoreApi for all flow tests"""
    with patch('worker.core_api.CoreApi') as mock_api_class:
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        # Default successful responses
        mock_api.get_bot_config.return_value = {
            "id": "test_bot_1",
            "name": "Test Bot",
            "type": "analyst_bot",
            "parameters": {
                "REGULAR_EXPRESSION": "test.*pattern",
                "ATTRIBUTE_NAME": "test_attribute"
            }
        }
        
        yield mock_api


@pytest.fixture
def sample_bot_request():
    """Sample bot task request"""
    return BotTaskRequest(
        bot_id=1,
        filter={"SOURCE": "test_source"}
    )
