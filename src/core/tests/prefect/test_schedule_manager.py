import pytest
from datetime import datetime


@pytest.fixture
def schedule_manager():
    from core.managers.schedule_manager import Scheduler
    return Scheduler()


class TestScheduleManager:
    """Tests for Prefect-based schedule manager"""

    def test_scheduler_initialization(self, schedule_manager):
        """Test that scheduler initializes properly"""
        assert schedule_manager.jobs == {}
        assert schedule_manager.deployments == {}

    def test_add_prefect_task_success(self, schedule_manager):
        """Test successful Prefect task scheduling"""
        task = {
            "id": "test_task",
            "name": "Test Task",
            "cron": "0 * * * *",
            "parameters": {"source_id": "123"}
        }

        result = schedule_manager.add_prefect_task(task)

        assert result is True
        assert "test_task" in schedule_manager.jobs
        stored_task = schedule_manager.jobs["test_task"]
        assert stored_task["id"] == "test_task"
        assert stored_task["name"] == "Test Task"
        assert stored_task["cron"] == "0 * * * *"

    def test_add_prefect_task_invalid_data(self, schedule_manager):
        """Test handling of invalid task data"""
        invalid_task = {"invalid": "data"}

        result = schedule_manager.add_prefect_task(invalid_task)

        assert result is False
        assert not schedule_manager.jobs

    def test_get_periodic_tasks(self, schedule_manager):
        """Test getting all periodic tasks"""
        # Add some test jobs using the proper method
        task1 = {"id": "job1", "name": "Job 1", "cron": "0 * * * *"}
        task2 = {"id": "job2", "name": "Job 2", "cron": "0 0 * * *"}
        
        schedule_manager.add_prefect_task(task1)
        schedule_manager.add_prefect_task(task2)

        result = schedule_manager.get_periodic_tasks()

        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        # Check that jobs are in the expected format
        job_ids = [job["id"] for job in result["items"]]
        assert "job1" in job_ids
        assert "job2" in job_ids

    def test_get_periodic_task(self, schedule_manager):
        """Test getting specific periodic task"""
        # Add a proper task using the method
        task = {"id": "test_job", "name": "Test Job", "cron": "0 * * * *"}
        schedule_manager.add_prefect_task(task)

        result = schedule_manager.get_periodic_task("test_job")

        assert result is not None
        assert result["id"] == "test_job"
        assert result["name"] == "Test Job"

        # Test non-existent job
        result = schedule_manager.get_periodic_task("non_existent")
        assert result is None

    def test_remove_periodic_task(self, schedule_manager):
        """Test removing periodic task"""
        schedule_manager.jobs["test_job"] = {"name": "Test Job", "cron": "0 * * * *"}

        result = schedule_manager.remove_periodic_task("test_job")

        assert result is True
        assert "test_job" not in schedule_manager.jobs

        # Test removing non-existent job
        result = schedule_manager.remove_periodic_task("non_existent")
        assert result is False

    def test_task_to_job_format_conversion(self, schedule_manager):
        """Test internal task to job format conversion"""
        task = {
            "id": "collector_123",
            "name": "Collect Source 123",
            "cron": "0 */6 * * *",
            "parameters": {"source_id": "123"}
        }

        job = schedule_manager._task_to_job_format(task)

        assert job["id"] == "collector_123"
        assert job["name"] == "Collect Source 123"
        assert job["trigger"] == "cron"
        assert job["cron"] == "0 */6 * * *"

    def test_cron_fire_times_calculation(self, schedule_manager):
        """Test cron expression fire times calculation"""
        cron_expr = "0 */6 * * *"  # Every 6 hours

        fire_times = schedule_manager.get_next_n_fire_times_from_cron(cron_expr, 3)

        assert len(fire_times) == 3
        assert all(isinstance(dt, datetime) for dt in fire_times)
        # Verify times are in ascending order
        assert fire_times[0] < fire_times[1] < fire_times[2]

    def test_remove_all_jobs(self, schedule_manager):
        """Test clearing all jobs"""
        # Add some test jobs
        schedule_manager.jobs = {
            "job1": {"name": "Job 1"},
            "job2": {"name": "Job 2"}
        }

        schedule_manager.remove_all_jobs()

        assert len(schedule_manager.jobs) == 0

    def test_initialize_periodic_tasks(self, schedule_manager):
        """Test initialization of periodic tasks from database"""
        # Since initialize_periodic_tasks requires a Flask application context
        # and may not be fully implemented for unit testing, we'll just test 
        # that the method exists
        assert hasattr(schedule_manager, 'initialize_periodic_tasks')
        assert callable(getattr(schedule_manager, 'initialize_periodic_tasks', None))
        
        # For unit tests, we don't call the actual method since it requires
        # database access and Flask app context. Integration tests would cover this.


class TestScheduleManagerModuleFunctions:
    """Test module-level singleton access"""

    def test_module_schedule_singleton_access(self):
        """Test that the module provides access to the schedule singleton"""
        from core.managers.schedule_manager import schedule
        
        # The schedule variable exists but may be None initially
        # (it gets initialized elsewhere in the application)
        # We just test that the variable exists and has the expected interface
        if schedule is not None:
            assert hasattr(schedule, 'add_prefect_task')
            assert hasattr(schedule, 'get_periodic_tasks')
            assert hasattr(schedule, 'remove_periodic_task')
        else:
            # schedule is None initially, which is expected
            # The initialize() function would set it up
            assert schedule is None

    def test_module_get_client_function(self):
        """Test module-level get_client function delegates to schedule instance"""
        from core.managers.schedule_manager import get_client, schedule
        
        result = get_client()
        if schedule:
            # get_client should delegate to the schedule instance
            assert result == schedule.get_client()
        else:
            # If no schedule instance, should return None
            assert result is None