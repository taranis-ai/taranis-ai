"""Tests for worker cron configuration"""

import pytest
from unittest.mock import MagicMock, patch

from worker.cron_config import load_cron_jobs, TASK_FUNCTION_MAP


class TestLoadCronJobs:
    """Test the load_cron_jobs function"""

    @pytest.fixture
    def mock_core_api(self):
        """Mock CoreApi that returns cron job configurations"""
        with patch("worker.cron_config.CoreApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            yield mock_api

    @pytest.fixture
    def sample_cron_jobs(self):
        """Sample cron job configurations from Core API"""
        return [
            {
                "task": "collector_task",
                "queue": "collectors",
                "args": ["source-123", False],
                "cron": "0 * * * *",
                "task_id": "collect_rss_source-123",
                "name": "Test RSS Source",
            },
            {
                "task": "bot_task",
                "queue": "bots",
                "args": ["bot-456"],
                "cron": "0 2 * * *",
                "task_id": "bot_bot-456",
                "name": "Test IOC Bot",
            },
            {
                "task": "cleanup_token_blacklist",
                "queue": "misc",
                "args": [],
                "cron": "0 2 * * *",
                "task_id": "cleanup_token_blacklist",
                "name": "Cleanup Token Blacklist",
            },
        ]

    def test_load_cron_jobs_registers_all_jobs(self, mock_core_api, sample_cron_jobs):
        """Test that load_cron_jobs registers all jobs from Core API"""
        mock_core_api.get_cron_jobs.return_value = sample_cron_jobs
        mock_scheduler = MagicMock()

        load_cron_jobs(scheduler=mock_scheduler)

        # Verify all jobs were registered
        assert mock_scheduler.register.call_count == 3

        # Verify each job was registered with correct parameters
        calls = mock_scheduler.register.call_args_list

        # First call: collector_task
        assert calls[0][1]["queue_name"] == "collectors"
        assert calls[0][1]["args"] == ("source-123", False)
        assert calls[0][1]["cron"] == "0 * * * *"

        # Second call: bot_task
        assert calls[1][1]["queue_name"] == "bots"
        assert calls[1][1]["args"] == ("bot-456",)
        assert calls[1][1]["cron"] == "0 2 * * *"

        # Third call: cleanup_token_blacklist
        assert calls[2][1]["queue_name"] == "misc"
        assert calls[2][1]["args"] == ()
        assert calls[2][1]["cron"] == "0 2 * * *"

    def test_load_cron_jobs_maps_task_names_to_functions(self, mock_core_api, sample_cron_jobs):
        """Test that task names are correctly mapped to actual functions"""
        mock_core_api.get_cron_jobs.return_value = sample_cron_jobs
        mock_scheduler = MagicMock()

        load_cron_jobs(scheduler=mock_scheduler)

        calls = mock_scheduler.register.call_args_list

        # Verify correct functions were registered
        from worker.collectors.collector_tasks import collector_task
        from worker.bots.bot_tasks import bot_task
        from worker.misc.misc_tasks import cleanup_token_blacklist

        assert calls[0][0][0] == collector_task
        assert calls[1][0][0] == bot_task
        assert calls[2][0][0] == cleanup_token_blacklist

    def test_load_cron_jobs_skips_unknown_tasks(self, mock_core_api):
        """Test that unknown task names are skipped with a warning"""
        mock_core_api.get_cron_jobs.return_value = [
            {
                "task": "unknown_task",
                "queue": "test",
                "args": [],
                "cron": "0 * * * *",
                "task_id": "unknown",
                "name": "Unknown Task",
            },
            {
                "task": "collector_task",
                "queue": "collectors",
                "args": ["source-123", False],
                "cron": "0 * * * *",
                "task_id": "collect_rss_source-123",
                "name": "Test Source",
            },
        ]
        mock_scheduler = MagicMock()

        with patch("worker.cron_config.logger") as mock_logger:
            load_cron_jobs(scheduler=mock_scheduler)

            # Should log warning for unknown task
            mock_logger.warning.assert_called_once()
            assert "Unknown task function" in str(mock_logger.warning.call_args)

        # Should only register the known task
        assert mock_scheduler.register.call_count == 1

    def test_load_cron_jobs_handles_empty_response(self, mock_core_api):
        """Test handling of empty cron jobs list"""
        mock_core_api.get_cron_jobs.return_value = []
        mock_scheduler = MagicMock()

        with patch("worker.cron_config.logger") as mock_logger:
            load_cron_jobs(scheduler=mock_scheduler)

            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "No cron jobs returned" in str(mock_logger.warning.call_args)

        # Should not register any jobs
        assert mock_scheduler.register.call_count == 0

    def test_load_cron_jobs_handles_none_response(self, mock_core_api):
        """Test handling of None response from API"""
        mock_core_api.get_cron_jobs.return_value = None
        mock_scheduler = MagicMock()

        with patch("worker.cron_config.logger") as mock_logger:
            load_cron_jobs(scheduler=mock_scheduler)

            # Should log warning
            mock_logger.warning.assert_called_once()

        # Should not register any jobs
        assert mock_scheduler.register.call_count == 0

    def test_load_cron_jobs_uses_global_register_without_scheduler(self, mock_core_api, sample_cron_jobs):
        """Test that global register is used when no scheduler is provided"""
        mock_core_api.get_cron_jobs.return_value = sample_cron_jobs

        with patch("worker.cron_config.global_register") as mock_global_register:
            load_cron_jobs(scheduler=None)

            # Should use global_register
            assert mock_global_register.call_count == 3

    def test_load_cron_jobs_converts_args_to_tuple(self, mock_core_api):
        """Test that args list is converted to tuple for registration"""
        mock_core_api.get_cron_jobs.return_value = [
            {
                "task": "collector_task",
                "queue": "collectors",
                "args": ["source-123", False],
                "cron": "0 * * * *",
                "task_id": "collect_rss_source-123",
                "name": "Test Source",
            }
        ]
        mock_scheduler = MagicMock()

        load_cron_jobs(scheduler=mock_scheduler)

        # Verify args were converted to tuple
        call_args = mock_scheduler.register.call_args_list[0]
        assert isinstance(call_args[1]["args"], tuple)
        assert call_args[1]["args"] == ("source-123", False)

    def test_load_cron_jobs_raises_on_api_exception(self, mock_core_api):
        """Test that exceptions from Core API are raised"""
        mock_core_api.get_cron_jobs.side_effect = Exception("API Error")
        mock_scheduler = MagicMock()

        with pytest.raises(Exception, match="API Error"):
            load_cron_jobs(scheduler=mock_scheduler)

        # Should not register any jobs
        assert mock_scheduler.register.call_count == 0

    def test_task_function_map_completeness(self):
        """Test that all expected task functions are in the map"""
        required_tasks = ["collector_task", "bot_task", "cleanup_token_blacklist"]

        for task in required_tasks:
            assert task in TASK_FUNCTION_MAP, f"Missing task in TASK_FUNCTION_MAP: {task}"
            assert callable(TASK_FUNCTION_MAP[task]), f"Task function not callable: {task}"

    def test_load_cron_jobs_logs_registration_info(self, mock_core_api, sample_cron_jobs):
        """Test that job registration is logged"""
        mock_core_api.get_cron_jobs.return_value = sample_cron_jobs
        mock_scheduler = MagicMock()

        with patch("worker.cron_config.logger") as mock_logger:
            load_cron_jobs(scheduler=mock_scheduler)

            # Should log each job registration
            info_calls = [call for call in mock_logger.info.call_args_list]
            assert len(info_calls) >= 3  # At least one per job

            # Should log final count
            final_log = str(info_calls[-1])
            assert "Registered 3 cron jobs" in final_log
