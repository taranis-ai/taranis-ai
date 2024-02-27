import json
import pytest
from core.managers.sse_manager import sse_manager
from unittest.mock import patch

# Mock data
test_report_item_data = {"report_item_id": 1, "status": "updated"}
test_product_data = {"product_id": 12, "status": "rendered"}
user_id = "user_123"
report_item_id = 1

def test_sse_publish():
    """Verify SSE publishes correctly to the listeners """
    listener_queue = sse_manager.sse.listen()
    event_name = "report-item-updated"
    sse_manager.report_item_updated(test_report_item_data)

    expected_message = f"event: {event_name}\ndata: {json.dumps(test_report_item_data)}\n\n"
    assert not listener_queue.empty()
    message = listener_queue.get_nowait()
    assert message == expected_message

@pytest.mark.parametrize("data, event, expected_output", [
    ({"key": "value"}, "test-event", 'event: test-event\ndata: {"key": "value"}\n\n'),
    ({"key": "value"}, None, 'data: {"key": "value"}\n\n')
])

def test_format_sse(data, event, expected_output):
    """Verify the format_sse method formats messages correctly with and without an event."""
    assert sse_manager.sse.format_sse(data, event) == expected_output, "SSE format_sse output does not match expected"
@patch('core.managers.sse.SSE.publish')
def test_news_items_updated(mock_publish):
    """Test news_items_updated method publishes correct event."""
    sse_manager.news_items_updated()
    mock_publish.assert_called_once_with({}, event="news-items-updated")

@patch('core.managers.sse.SSE.publish')
def test_report_item_updated(mock_publish):
    """Test report_item_updated method publishes correct data and event."""
    sse_manager.report_item_updated(test_report_item_data)
    mock_publish.assert_called_once_with(test_report_item_data, event="report-item-updated")

@patch('core.managers.sse.SSE.publish')
def test_product_rendered(mock_publish):
    """Test product_rendered method publishes correct data and event."""
    sse_manager.product_rendered(test_product_data)
    mock_publish.assert_called_once_with(test_product_data, event="product-rendered")

@patch('core.managers.sse.SSE.publish')
def test_report_item_lock(mock_publish):
    """Test report_item_lock method locks items and publishes correct event."""
    sse_manager.report_item_lock(report_item_id, user_id)
    expected_data = {"report_item_id": report_item_id, "user_id": user_id}
    mock_publish.assert_called_with(expected_data, event="report-item-locked")

@patch('core.managers.sse.SSE.publish')
def test_report_item_unlock(mock_publish):
    """Test report_item_unlock method unlocks items and publishes correct event."""
    sse_manager.report_item_lock(report_item_id, user_id)
    sse_manager.report_item_unlock(report_item_id, user_id)
    expected_data = {"report_item_id": report_item_id, "user_id": user_id}
    mock_publish.assert_called_with(expected_data, event="report-item-unlocked")