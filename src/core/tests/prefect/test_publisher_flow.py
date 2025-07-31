from unittest.mock import patch, MagicMock
from worker.flows.publisher_task_flow import publisher_task_flow
from models.publisher import PublisherTaskRequest


@patch("worker.flows.publisher_task_flow.Product")
@patch("worker.flows.publisher_task_flow.Publisher")
def test_publisher_flow_runs(mock_publisher_class, mock_product_class):
    # Mock the Product
    mock_product = MagicMock()
    mock_product.id = "dummy_product_id"
    mock_product.get_render.return_value = MagicMock(data=b"pdf-bytes", mime_type="application/pdf")
    mock_product_class.get.return_value = mock_product

    # Mock the Publisher
    mock_publisher = MagicMock()
    mock_publisher.id = "dummy_publisher_id"
    mock_publisher.type = "dummy"
    mock_publisher_class.get.return_value = mock_publisher

    # Patch the publishing logic
    with patch("worker.flows.publisher_task_flow.__import__") as mock_import:
        mock_task_class = MagicMock()
        mock_task_class.return_value.publish.return_value = "success"
        mock_import.return_value = MagicMock(PublisherTask=mock_task_class)

        # Run the flow
        request = PublisherTaskRequest(product_id="dummy_product_id", publisher_id="dummy_publisher_id")
        result = publisher_task_flow.fn(request)

        assert "message" in result
        assert "result" in result
        assert result["result"] == "success"
