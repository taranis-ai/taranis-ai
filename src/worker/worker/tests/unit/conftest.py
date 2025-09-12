import pytest
from unittest.mock import Mock, patch


@pytest.fixture(scope="function")
def mock_core_api():
    """Mock CoreApi for all flow tests"""
    with patch("worker.core_api.CoreApi") as mock_api_class:
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        # Default successful responses
        mock_api.get_bot_config.return_value = {
            "id": "test_bot_1",
            "name": "Test Bot",
            "type": "analyst_bot",
            "parameters": {"REGULAR_EXPRESSION": "test.*pattern", "ATTRIBUTE_NAME": "test_attribute"},
        }

        yield mock_api
