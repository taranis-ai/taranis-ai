from unittest.mock import patch, MagicMock
from worker.flows.presenter_task_flow import presenter_task_flow
from models.models.presenter import PresenterTaskRequest


@patch("worker.flows.presenter_task_flow.PRESENTER_REGISTRY", {"dummy": MagicMock()})
@patch("worker.flows.presenter_task_flow.Presenter")
@patch("worker.flows.presenter_task_flow.Product")
def test_presenter_flow_runs(mock_product_class, mock_presenter_class, mock_registry):
    # Mock the Product
    mock_product = MagicMock()
    mock_product.id = "dummy_product_id"
    mock_product.get_render.return_value = MagicMock(data=b"pdf-bytes", mime_type="application/pdf")
    mock_product_class.get.return_value = mock_product

    # Mock the Presenter
    mock_presenter = MagicMock()
    mock_presenter.id = "dummy_presenter_id"
    mock_presenter.type = "dummy"
    mock_presenter_class.get.return_value = mock_presenter

    # Also configure the mock registry to return a mock task with publish
    mock_task = MagicMock()
    mock_task.publish.return_value = "success"
    mock_registry["dummy"].return_value = mock_task

    # Run the flow
    request = PresenterTaskRequest(product_id="dummy_product_id", presenter_id="dummy_presenter_id")
    result = presenter_task_flow.fn(request)

    assert "message" in result
    assert "result" in result
    assert result["result"] == "success"
