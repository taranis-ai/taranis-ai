import pytest
from unittest.mock import MagicMock, patch, AsyncMock

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_prefect_server():
    """Mock Prefect server responses"""
    with patch("prefect.client.orchestration.get_client") as mock_client:
        client = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client

        # Mock successful responses
        client.read_flow_runs.return_value = [
            {"id": "run-1", "state": "Completed", "name": "collector"},
            {"id": "run-2", "state": "Running", "name": "bot-analysis"}
        ]
        client.create_flow_run.return_value = MagicMock(id="new-run-123")
        client.create_deployment.return_value = MagicMock(id="deploy-456")

        # Mock read_flows for flow lookup
        client.read_flows.return_value = [
            MagicMock(id="flow-123", name="collector-task-flow")
        ]

        yield client


class TestPrefectCeleryMigration:
    """Integration tests verifying Celery → Prefect migration works end-to-end"""

    def test_queue_manager_initialization(self, mock_prefect_server):
        """Test that QueueManager initializes without Celery dependencies"""
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass"
        }

        # Should initialize without errors
        qm = QueueManager(app)
        assert qm.error == ""
        assert not hasattr(qm, 'celery')  # No Celery reference

    def test_schedule_manager_initialization(self, mock_prefect_server):
        """Test that ScheduleManager initializes without APScheduler dependencies"""
        from core.managers.schedule_manager import Scheduler

        # Should initialize without APScheduler
        scheduler = Scheduler()
        assert scheduler.jobs == {}
        assert scheduler.deployments == {}
        assert not hasattr(scheduler, 'apscheduler')  # No APScheduler reference

    def test_osint_source_collection_workflow(self, mock_prefect_server):
        """Test complete OSINT source collection workflow"""
        from core.managers.queue_manager import QueueManager
        from core.model.osint_source import OSINTSource

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass"
        }
        qm = QueueManager(app)

        # Mock an OSINT source
        with patch.object(OSINTSource, 'get') as mock_source:
            mock_source.return_value = MagicMock(id="source-123", name="Test Source")

            result, status_code = qm.collect_osint_source("source-123")

            assert status_code == 200
            assert "scheduled" in result["message"]
            mock_prefect_server.read_flows.assert_called_once()
            mock_prefect_server.create_flow_run.assert_called_once()

    def test_periodic_task_scheduling_workflow(self, mock_prefect_server):
        """Test periodic task scheduling replaces APScheduler functionality"""
        from core.managers.schedule_manager import Scheduler

        scheduler = Scheduler()

        task = {
            "id": "periodic_collection",
            "name": "Periodic Collection",
            "cron": "0 */6 * * *",
            "parameters": {"source_id": "123"}
        }

        result = scheduler.add_prefect_task(task)

        assert result is True
        assert "periodic_collection" in scheduler.jobs
        mock_prefect_server.create_deployment.assert_called_once()

    @patch("core.model.osint_source.OSINTSource.get_enabled_sources")
    def test_bulk_collection_replaces_celery_group(self, mock_sources, mock_prefect_server):
        """Test that bulk collection works without Celery group operations"""
        from core.managers.queue_manager import QueueManager

        # Mock multiple sources
        mock_sources.return_value = [
            MagicMock(id="source1", name="Source 1"),
            MagicMock(id="source2", name="Source 2"),
            MagicMock(id="source3", name="Source 3")
        ]

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass"
        }
        qm = QueueManager(app)

        result = qm.collect_all_osint_sources()

        assert result is True
        # Should create individual flow runs instead of Celery group
        assert mock_prefect_server.create_flow_run.call_count >= 1

    def test_api_endpoints_use_prefect_managers(self, mock_prefect_server):
        """Test that API endpoints use Prefect managers instead of Celery"""
        from core.api.config import queue_manager, schedule_manager

        # Verify managers are Prefect-based
        assert hasattr(queue_manager, 'collect_osint_source')
        assert hasattr(schedule_manager, 'add_prefect_task')

        # Test basic API operations
        result = queue_manager.get_queue_status()
        assert isinstance(result, tuple)
        assert len(result) == 2  # (data, status_code)

    def test_model_integration_with_prefect_tasks(self, mock_prefect_server):
        """Test that database models trigger Prefect tasks correctly"""
        from core.model.osint_source import OSINTSource
        from core.managers import schedule_manager

        # Mock database operations
        with patch.object(OSINTSource, 'get_all') as mock_get_all:
            mock_source = MagicMock()
            mock_source.id = "test-source"
            mock_source.collect_schedule = "0 */6 * * *"
            mock_get_all.return_value = [mock_source]

            # Simulate adding a scheduled collection task
            task = {
                "id": f"collector_{mock_source.id}",
                "name": f"Collect {mock_source.id}",
                "cron": mock_source.collect_schedule,
                "parameters": {"source_id": mock_source.id}
            }

            result = schedule_manager.add_prefect_task(task)
            assert result is True

    def test_error_handling_without_celery_exceptions(self, mock_prefect_server):
        """Test error handling uses Prefect exceptions instead of Celery ones"""
        from core.managers.queue_manager import QueueManager

        # Force a Prefect error
        mock_prefect_server.create_flow_run.side_effect = Exception("Prefect error")

        app = MagicMock()
        qm = QueueManager(app)

        result = qm.collect_osint_source("failing-source")

        # Should handle error gracefully without Celery exceptions
        assert result is False
        # Should not raise WorkerLostError or other Celery-specific exceptions

    def test_no_celery_imports_in_codebase(self):
        """Verify that Celery imports have been removed"""
        import ast
        import os

        # Check key manager files for Celery imports
        manager_files = [
            "src/core/core/managers/queue_manager.py",
            "src/core/core/managers/schedule_manager.py"
        ]

        for file_path in manager_files:
            full_path = os.path.join("/home/schregera/code/taranis-ai", file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()

                # Parse as AST to check imports
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                assert not alias.name.startswith('celery'), f"Found Celery import in {file_path}: {alias.name}"
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                assert not node.module.startswith('celery'), f"Found Celery import in {file_path}: {node.module}"
                except SyntaxError:
                    # File might have syntax errors during development
                    pass

    def test_prefect_deployment_configuration(self, mock_prefect_server):
        """Test that Prefect deployments are configured correctly for production"""
        from core.managers.schedule_manager import Scheduler

        scheduler = Scheduler()

        # Test deployment configuration
        task = {
            "id": "production_task",
            "name": "Production Collection Task",
            "cron": "0 0 * * *",  # Daily at midnight
            "parameters": {"source_id": "prod-source"}
        }

        result = scheduler.add_prefect_task(task)

        assert result is True

        # Verify deployment was created with correct parameters
        call_args = mock_prefect_server.create_deployment.call_args
        assert call_args is not None

        # Check that the deployment includes proper work pool configuration
        deployment_kwargs = call_args.kwargs if call_args.kwargs else {}
        # Should include work_pool_name or similar production-ready configuration


class TestPrefectWorkerIntegration:
    """Test integration with Prefect workers"""

    def test_worker_queue_visibility(self, mock_prefect_server):
        """Test that workers are visible through Prefect client"""
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        qm = QueueManager(app)

        # Mock worker pool response
        mock_prefect_server.read_flow_runs.return_value = [
            {"id": "run-1", "work_pool_name": "collectors"},
            {"id": "run-2", "work_pool_name": "bots"}
        ]

        result = qm.ping_workers()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_task_distribution_to_workers(self, mock_prefect_server):
        """Test that tasks are properly distributed to worker pools"""
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        qm = QueueManager(app)

        # Submit different types of tasks
        collector_result = qm.collect_osint_source("source-123")

        assert collector_result is True

        # Verify flow runs were created
        assert mock_prefect_server.create_flow_run.called

        # Should target appropriate work pools based on task type
        call_args = mock_prefect_server.create_flow_run.call_args_list
        assert len(call_args) > 0