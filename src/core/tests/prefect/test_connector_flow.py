from unittest.mock import patch, MagicMock
from worker.flows.connector_task_flow import connector_task_flow
from models.connector import ConnectorTaskRequest


@patch("worker.flows.connector_task_flow.execute_connector")
@patch("worker.flows.connector_task_flow.get_stories_by_id") 
@patch("worker.flows.connector_task_flow.get_connector_instance")
@patch("worker.flows.connector_task_flow.get_connector_config")
def test_connector_flow_runs(mock_get_config, mock_get_instance, mock_get_stories, mock_execute):
    # Mock connector config
    mock_get_config.return_value = ({"type": "misp_connector", "api_url": "http://test"}, "misp_connector")
    
    # Mock connector instance
    mock_connector = MagicMock()
    mock_get_instance.return_value = mock_connector

    # Mock stories
    mock_stories = [{"id": "story1", "title": "Test Story"}]
    mock_get_stories.return_value = mock_stories
    
    # Mock connector execution result
    mock_execute.return_value = "success"

    # Create test request
    request = ConnectorTaskRequest(
        connector_id="dummy_connector_id", 
        story_ids=["story1", "story2"]
    )
    
    # Run the flow 
    result = connector_task_flow.fn(request)
    
    # Verify the result
    assert result == "success"
    
    # Verify mocks were called
    mock_get_config.assert_called_once_with("dummy_connector_id")
    mock_get_instance.assert_called_once_with("misp_connector")
    mock_get_stories.assert_called_once_with(["story1", "story2"])
    mock_execute.assert_called_once_with(mock_connector, {"type": "misp_connector", "api_url": "http://test"}, mock_stories)
