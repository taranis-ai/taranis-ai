from unittest.mock import patch, MagicMock
from worker.flows.connector_task_flow import connector_task_flow
from models.models.connector import ConnectorTaskRequest


@patch("worker.flows.connector_task_flow.Product")
@patch("worker.flows.connector_task_flow.Connector")
@patch("worker.flows.connector_task_flow.CONNECTOR_REGISTRY", {"dummy": MagicMock()})
def test_connector_flow_runs(mock_connector_class, mock_product_class):
    # Mock the Product
    mock_product = MagicMock()
    mock_product.id = "dummy_product_id"
    mock_product.get_render.return_value = MagicMock(data=b"pdf-bytes", mime_type="application/pdf")
    mock_product_class.get.return_value = mock_product

    # Mock the Connector
    mock_connector = MagicMock()
    mock_connector.id = "dummy_connector_id"
    mock_connector.type = "dummy"
    mock_connector_class.get.return_value = mock_connector

    # Patch the connector logic
    mock_task_class = MagicMock()
    mock_task_class.return_value.run.return_value = "success"

    with patch("worker.flows.connector_task_flow.__import__") as mock_import:
        mock_import.return_value = MagicMock(ConnectorTask=mock_task_class)

        # Run the flow
        request = ConnectorTaskRequest(product_id="dummy_product_id", connector_id="dummy_connector_id")
        result = connector_task_flow.fn(request)

        assert "message" in result
        assert "result" in result
        assert result["result"] == "success"
