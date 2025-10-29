import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

models_prefect = pytest.importorskip("models.prefect")

CollectorTaskRequest = models_prefect.CollectorTaskRequest
PresenterTaskRequest = models_prefect.PresenterTaskRequest
PublisherTaskRequest = models_prefect.PublisherTaskRequest
ConnectorTaskRequest = models_prefect.ConnectorTaskRequest
BotTaskRequest = models_prefect.BotTaskRequest
WordListTaskRequest = models_prefect.WordListTaskRequest


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

    @patch("core.managers.queue_manager.run_deployment")
    def test_collect_osint_source(self, mock_run_deployment, queue_manager):
        """Test OSINT source collection task"""
        mock_run_deployment.return_value = MagicMock(id="flow-run-123")

        payload, status = queue_manager.collect_osint_source("source-123")

        assert status == 200
        assert payload["result"] == "flow-run-123"
        mock_run_deployment.assert_called_once_with(
            name="collector-task-flow/default",
            parameters={"request": ANY},
            timeout=0,
        )
        call_params = mock_run_deployment.call_args.kwargs["parameters"]["request"]
        assert call_params["source_id"] == "source-123"
        assert call_params["preview"] is False

    @patch("core.managers.queue_manager.run_deployment")
    def test_preview_osint_source(self, mock_run_deployment, queue_manager):
        """Test OSINT source preview task"""
        mock_run_deployment.return_value = MagicMock(id="flow-run-456")

        payload, status = queue_manager.preview_osint_source("source-456")

        assert status == 200
        assert payload["result"] == "flow-run-456"
        call_params = mock_run_deployment.call_args.kwargs["parameters"]["request"]
        assert call_params["preview"] is True

    @patch("core.managers.queue_manager.run_deployment")
    def test_collect_all_osint_sources(self, mock_run_deployment, queue_manager):
        """Test collecting all OSINT sources"""
        with patch("core.model.osint_source.OSINTSource.get_all_for_collector") as mock_sources:
            mock_sources.return_value = [
                MagicMock(id="source1"),
                MagicMock(id="source2"),
                MagicMock(id="source3"),
            ]

            payload, status = queue_manager.collect_all_osint_sources()

        assert status == 200
        assert payload["message"].startswith("Ran collector flow for 3")
        assert mock_run_deployment.call_count == 3

    @patch("core.managers.queue_manager.run_deployment")
    def test_push_to_connector(self, mock_run_deployment, queue_manager):
        """Test pushing stories to connector"""
        mock_run_deployment.return_value = MagicMock(id="connector-flow-123")

        story_ids = ["story1", "story2", "story3"]
        payload, status = queue_manager.push_to_connector("connector-123", story_ids)

        assert status == 200
        assert payload["result"] == "connector-flow-123"
        call_params = mock_run_deployment.call_args.kwargs["parameters"]["request"]
        assert call_params["connector_id"] == "connector-123"
        assert call_params["story_ids"] == story_ids

    @patch("core.managers.queue_manager.run_deployment")
    def test_pull_from_connector(self, mock_run_deployment, queue_manager):
        """Test pulling from connector"""
        mock_run_deployment.return_value = MagicMock(id="connector-pull-123")

        payload, status = queue_manager.pull_from_connector("connector-456")

        assert status == 200
        assert payload["result"] == "connector-pull-123"
        call_params = mock_run_deployment.call_args.kwargs["parameters"]["request"]
        assert call_params["story_ids"] is None

    @patch("core.managers.queue_manager.run_deployment")
    def test_update_empty_word_lists(self, mock_run_deployment, queue_manager):
        """Test word list update task"""
        mock_run_deployment.side_effect = [
            MagicMock(id="wordlist-flow-1"),
            MagicMock(id="wordlist-flow-2"),
        ]

        with patch("core.model.word_list.WordList.get_all_empty") as mock_lists:
            mock_lists.return_value = [
                MagicMock(id=1, name="List 1"),
                MagicMock(id=2, name="List 2"),
            ]

            results = queue_manager.update_empty_word_lists()

        assert results == [
            {"word_list_id": 1, "status": "ok", "result": "wordlist-flow-1"},
            {"word_list_id": 2, "status": "ok", "result": "wordlist-flow-2"},
        ]
        assert mock_run_deployment.call_count == 2

    @patch("core.managers.queue_manager.run_deployment", side_effect=Exception("Prefect server unreachable"))
    def test_task_execution_failure_handling(self, mock_run_deployment, queue_manager):
        """Test error handling when Prefect task execution fails"""

        payload, status = queue_manager.collect_osint_source("source-fail")

        assert status == 500
        assert payload["error"] == "Failed to schedule collection for source source-fail"


class TestPrefectTaskModels:
    """Test Prefect task request models"""

    def test_collector_task_request_model(self):
        """Test CollectorTaskRequest model validation"""
        # Valid request
        task = CollectorTaskRequest(source_id="source-123", preview=True, manual=False)
        assert (task.source_id, task.preview, task.manual) == ("source-123", True, False)

        # Minimal request
        task_minimal = CollectorTaskRequest(source_id="source-456")
        assert (task_minimal.source_id, task_minimal.preview, task_minimal.manual) == ("source-456", False, False)

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

    def test_get_queue_status_uses_asyncio_run(self, queue_manager):
        """Ensure queue status delegates to asyncio run loop"""
        mock_client = AsyncMock()
        mock_client.read_flow_runs.return_value = []
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client

        with patch("core.managers.queue_manager.get_client", return_value=mock_context):
            with patch("core.managers.queue_manager.asyncio.run", wraps=asyncio.run) as mock_run:
                payload, status = queue_manager.get_queue_status()

        assert status == 200
        assert payload["status"] == "Prefect agent reachable"
        mock_run.assert_called_once()

    @patch("core.managers.queue_manager.get_client")
    def test_list_worker_queues_uses_prefect_client(self, mock_get_client, queue_manager):
        """Verify Prefect client context manager is used for async listing"""
        mock_client = AsyncMock()
        mock_client.read_flow_runs.return_value = ["run"]
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_client
        mock_get_client.return_value = mock_context_manager

        runs = asyncio.run(queue_manager.list_worker_queues(limit=5))

        assert runs == ["run"]
        mock_get_client.assert_called_once()
        mock_client.read_flow_runs.assert_awaited_once_with(limit=5)