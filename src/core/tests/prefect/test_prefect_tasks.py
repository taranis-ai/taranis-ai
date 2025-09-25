import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from models import (
    CollectorTaskRequest, 
    PresenterTaskRequest, 
    PublisherTaskRequest, 
    ConnectorTaskRequest, 
    BotTaskRequest,
    WordListTaskRequest
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config = {"QUEUE_BROKER_HOST": "localhost", "QUEUE_BROKER_USER": "test", "QUEUE_BROKER_PASSWORD": "test"}
    return app


@pytest.fixture
def queue_manager(mock_app):
    from core.managers.queue_manager import QueueManager
    qm = QueueManager(mock_app)
    qm.error = ""
    return qm


class TestQueueManagerTaskExecution:
    """Test specific Prefect task execution methods"""

    @patch("core.managers.queue_manager.get_client")
    def test_collect_osint_source(self, mock_get_client, queue_manager):
        """Test OSINT source collection task"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="flow-run-123")

        result = queue_manager.collect_osint_source("source-123")

        assert result is True
        mock_client.create_flow_run.assert_called_once()
        # Verify the correct flow was called with correct parameters
        call_args = mock_client.create_flow_run.call_args
        assert "collector-flow" in str(call_args)

    @patch("core.managers.queue_manager.get_client")
    def test_preview_osint_source(self, mock_get_client, queue_manager):
        """Test OSINT source preview task"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="flow-run-456")

        result = queue_manager.preview_osint_source("source-456")

        assert result is True
        mock_client.create_flow_run.assert_called_once()
        # Verify preview parameter is set correctly
        call_args = mock_client.create_flow_run.call_args
        assert "preview" in str(call_args) or "True" in str(call_args)

    @patch("core.managers.queue_manager.get_client")
    def test_collect_all_osint_sources(self, mock_get_client, queue_manager):
        """Test collecting all OSINT sources"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="flow-run-all")

        with patch("core.model.osint_source.OSINTSource.get_all_enabled") as mock_sources:
            mock_sources.return_value = [
                MagicMock(id="source1"),
                MagicMock(id="source2"),
                MagicMock(id="source3")
            ]

            result = queue_manager.collect_all_osint_sources()

            assert result is True
            # Should create flow runs for each enabled source
            assert mock_client.create_flow_run.call_count >= 1

    @patch("core.managers.queue_manager.get_client")
    def test_push_to_connector(self, mock_get_client, queue_manager):
        """Test pushing stories to connector"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="connector-flow-123")

        story_ids = ["story1", "story2", "story3"]
        result = queue_manager.push_to_connector("connector-123", story_ids)

        assert result is True
        mock_client.create_flow_run.assert_called_once()
        # Verify connector parameters
        call_args = mock_client.create_flow_run.call_args
        assert "connector-123" in str(call_args)

    @patch("core.managers.queue_manager.get_client")
    def test_pull_from_connector(self, mock_get_client, queue_manager):
        """Test pulling from connector"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="connector-pull-123")

        result = queue_manager.pull_from_connector("connector-456")

        assert result is True
        mock_client.create_flow_run.assert_called_once()

    @patch("core.managers.queue_manager.get_client")
    def test_update_empty_word_lists(self, mock_get_client, queue_manager):
        """Test word list update task"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_client.create_flow_run.return_value = MagicMock(id="wordlist-flow-123")

        with patch("core.model.word_list.WordList.get_empty_word_lists") as mock_lists:
            mock_lists.return_value = [
                MagicMock(id=1, name="List 1"),
                MagicMock(id=2, name="List 2")
            ]

            result = queue_manager.update_empty_word_lists()

            assert result is True
            # Should create flow runs for empty word lists
            assert mock_client.create_flow_run.call_count >= 1

    @patch("core.managers.queue_manager.get_client")
    def test_task_execution_failure_handling(self, mock_get_client, queue_manager):
        """Test error handling when Prefect task execution fails"""
        mock_get_client.side_effect = Exception("Prefect server unreachable")

        result = queue_manager.collect_osint_source("source-fail")

        assert result is False


class TestPrefectTaskModels:
    """Test Prefect task request models"""

    def test_collector_task_request_model(self):
        """Test CollectorTaskRequest model validation"""
        # Valid request
        task = CollectorTaskRequest(source_id="source-123", preview=True, manual=False)
        assert task.source_id == "source-123"
        assert task.preview is True
        assert task.manual is False

        # Minimal request
        task_minimal = CollectorTaskRequest(source_id="source-456")
        assert task_minimal.source_id == "source-456"
        assert task_minimal.preview is False  # default
        assert task_minimal.manual is False   # default

    def test_presenter_task_request_model(self):
        """Test PresenterTaskRequest model validation"""
        task = PresenterTaskRequest(product_id="product-123", countdown=300)
        assert task.product_id == "product-123"
        assert task.countdown == 300

        # Default countdown
        task_default = PresenterTaskRequest(product_id="product-456")
        assert task_default.countdown == 0

    def test_publisher_task_request_model(self):
        """Test PublisherTaskRequest model validation"""
        task = PublisherTaskRequest(product_id="product-123", publisher_id="pub-456")
        assert task.product_id == "product-123"
        assert task.publisher_id == "pub-456"

    def test_connector_task_request_model(self):
        """Test ConnectorTaskRequest model validation"""
        story_ids = ["story1", "story2", "story3"]
        task = ConnectorTaskRequest(connector_id="conn-123", story_ids=story_ids)
        assert task.connector_id == "conn-123"
        assert task.story_ids == story_ids

        # Optional story_ids
        task_no_stories = ConnectorTaskRequest(connector_id="conn-456")
        assert task_no_stories.story_ids is None

    def test_bot_task_request_model(self):
        """Test BotTaskRequest model validation"""
        filter_dict = {"type": "analysis", "status": "active"}
        task = BotTaskRequest(bot_id="bot-123", filter=filter_dict)
        assert task.bot_id == "bot-123"
        assert task.filter == filter_dict

        # Optional filter
        task_no_filter = BotTaskRequest(bot_id="bot-456")
        assert task_no_filter.filter is None

    def test_word_list_task_request_model(self):
        """Test WordListTaskRequest model validation"""
        task = WordListTaskRequest(word_list_id=42)
        assert task.word_list_id == 42

        # Test validation error for invalid types
        with pytest.raises(ValueError):
            WordListTaskRequest(word_list_id="not-an-int")


class TestQueueManagerAsyncIntegration:
    """Test async integration points"""

    @patch("core.managers.queue_manager.asyncio.run")
    def test_async_method_wrapping(self, mock_asyncio_run, queue_manager):
        """Test that sync methods properly wrap async operations"""
        mock_asyncio_run.return_value = True

        result = queue_manager.collect_osint_source("source-123")

        assert result is True
        mock_asyncio_run.assert_called_once()

    @patch("core.managers.queue_manager.get_client")
    def test_prefect_client_context_manager(self, mock_get_client, queue_manager):
        """Test proper use of Prefect client context manager"""
        mock_client = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_client
        mock_get_client.return_value = mock_context_manager
        mock_client.create_flow_run.return_value = MagicMock(id="test-run")

        queue_manager.collect_osint_source("source-test")

        # Verify context manager was used correctly
        mock_get_client.assert_called_once()
        mock_context_manager.__aenter__.assert_called_once()