from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def prefect_mocks():
    """Provide patched Prefect helpers used by queue manager and scheduler."""
    with patch("core.managers.queue_manager.get_client") as mock_get_client, \
         patch("core.managers.queue_manager.run_deployment") as mock_run_deployment:
        client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = client

        client.read_flow_runs.return_value = [
            MagicMock(id="run-1", state_name="Completed", flow_name="collector", created=None),
            MagicMock(id="run-2", state_name="Running", flow_name="bot-analysis", created=None),
        ]
        client.read_flows.return_value = [MagicMock(id="flow-collector", name="collector-task-flow")]

        mock_run_deployment.return_value = MagicMock(id="flow-run-123")

        from core.managers import schedule_manager as schedule_module

        original_schedule = schedule_module.schedule
        schedule_module.schedule = schedule_module.Scheduler()

        try:
            yield SimpleNamespace(client=client, run_deployment=mock_run_deployment)
        finally:
            schedule_module.schedule = original_schedule


class TestPrefectCeleryMigration:
    def test_queue_manager_initialization(self, prefect_mocks):
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }

        qm = QueueManager(app)

        assert qm.error == ""
        assert not hasattr(qm, "celery")

    def test_schedule_manager_initialization(self, prefect_mocks):
        from core.managers.schedule_manager import Scheduler

        scheduler = Scheduler()

        assert scheduler.jobs == {}
        assert scheduler.deployments == {}
        assert not hasattr(scheduler, "apscheduler")

    def test_osint_source_collection_workflow(self, prefect_mocks):
        from core.managers.queue_manager import QueueManager
        from core.model.osint_source import OSINTSource

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }
        qm = QueueManager(app)

        with patch.object(OSINTSource, "get") as mock_source:
            mock_source.return_value = MagicMock(id="source-123", name="Test Source")

            result, status_code = qm.collect_osint_source("source-123")

        assert status_code == 200
        assert "scheduled" in result["message"]
        prefect_mocks.run_deployment.assert_called_once()

    def test_periodic_task_scheduling_workflow(self, prefect_mocks):
        from core.managers.schedule_manager import Scheduler

        scheduler = Scheduler()

        task = {
            "id": "periodic_collection",
            "name": "Periodic Collection",
            "cron": "0 */6 * * *",
            "parameters": {"source_id": "123"},
        }

        result = scheduler.add_prefect_task(task)

        assert result is True
        assert "periodic_collection" in scheduler.jobs
        scheduled = scheduler.jobs["periodic_collection"]
        assert scheduled["flow_name"] == "collector-task-flow"
        assert scheduled["cron"] == "0 */6 * * *"

    @patch("core.model.osint_source.OSINTSource.get_all_for_collector")
    def test_bulk_collection_replaces_celery_group(self, mock_sources, prefect_mocks):
        from core.managers.queue_manager import QueueManager

        mock_sources.return_value = [
            MagicMock(id="source1", name="Source 1"),
            MagicMock(id="source2", name="Source 2"),
            MagicMock(id="source3", name="Source 3"),
        ]

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }
        qm = QueueManager(app)

        result, status_code = qm.collect_all_osint_sources()

        assert status_code == 200
        assert len(result["results"]) == len(mock_sources.return_value)
        assert prefect_mocks.run_deployment.call_count == len(mock_sources.return_value)

    def test_api_endpoints_use_prefect_managers(self, prefect_mocks):
        from core.api.config import OSINTSourceCollect

        view = OSINTSourceCollect()

        with patch("core.api.config._get_queue_manager") as mock_get_manager, \
             patch("core.api.config.osint_source.OSINTSource.get") as mock_get_source:
            manager = MagicMock()
            mock_get_manager.return_value = manager
            manager.collect_osint_source.return_value = ({"message": "ok"}, 200)
            mock_get_source.return_value = MagicMock()

            raw_post = getattr(OSINTSourceCollect.post, "__wrapped__", OSINTSourceCollect.post)
            wrapped_post = raw_post.__get__(view, OSINTSourceCollect)
            response = wrapped_post("source-123")

        assert response == ({"message": "ok"}, 200)
        manager.collect_osint_source.assert_called_once_with("source-123")

    def test_model_integration_with_prefect_tasks(self, prefect_mocks):
        from core.model.osint_source import OSINTSource
        from core.managers import schedule_manager

        with patch.object(OSINTSource, "get_all_for_collector") as mock_get_all:
            mock_source = MagicMock()
            mock_source.id = "test-source"
            mock_source.collect_schedule = "0 */6 * * *"
            mock_get_all.return_value = [mock_source]

            task = {
                "id": f"collector_{mock_source.id}",
                "name": f"Collect {mock_source.id}",
                "cron": mock_source.collect_schedule,
                "parameters": {"source_id": mock_source.id},
            }

            result = schedule_manager.add_prefect_task(task)

        assert result is True
        scheduler_instance = schedule_manager.schedule
        assert scheduler_instance is not None
        assert scheduler_instance.jobs[task["id"]]["flow_name"] == "collector-task-flow"

    def test_error_handling_without_celery_exceptions(self, prefect_mocks):
        from core.managers.queue_manager import QueueManager

        prefect_mocks.run_deployment.side_effect = Exception("Prefect error")

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }
        qm = QueueManager(app)

        result, status_code = qm.collect_osint_source("failing-source")

        assert status_code == 500
        assert "error" in result

    def test_no_celery_imports_in_codebase(self):
        import ast
        import os

        manager_files = [
            "src/core/core/managers/queue_manager.py",
            "src/core/core/managers/schedule_manager.py",
        ]

        for file_path in manager_files:
            full_path = os.path.join("/home/schregera/code/taranis-ai", file_path)
            if not os.path.exists(full_path):
                continue

            with open(full_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("celery"), (
                            f"Found Celery import in {file_path}: {alias.name}"
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("celery"), (
                        f"Found Celery import in {file_path}: {node.module}"
                    )

    def test_prefect_deployment_configuration(self, prefect_mocks):
        from core.managers.schedule_manager import Scheduler

        scheduler = Scheduler()

        task = {
            "id": "production_task",
            "name": "Production Collection Task",
            "cron": "0 0 * * *",
            "parameters": {"source_id": "prod-source"},
        }

        result = scheduler.add_prefect_task(task)

        assert result is True
        assert "production_task" in scheduler.jobs
        scheduled = scheduler.jobs["production_task"]
        assert scheduled["cron"] == "0 0 * * *"


class TestPrefectWorkerIntegration:
    def test_worker_queue_visibility(self, prefect_mocks):
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }
        qm = QueueManager(app)

        prefect_mocks.client.read_flow_runs.return_value = [
            MagicMock(id="run-1", work_pool_name="collectors"),
            MagicMock(id="run-2", work_pool_name="bots"),
        ]

        result = qm.ping_workers()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_task_distribution_to_workers(self, prefect_mocks):
        from core.managers.queue_manager import QueueManager

        app = MagicMock()
        app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test_user",
            "QUEUE_BROKER_PASSWORD": "test_pass",
        }
        qm = QueueManager(app)

        result, status_code = qm.collect_osint_source("source-123")

        assert status_code == 200
        assert prefect_mocks.run_deployment.called
