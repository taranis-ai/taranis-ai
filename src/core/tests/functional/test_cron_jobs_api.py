"""Tests for the /api/config/workers/cron-jobs endpoint"""


class TestCronJobsAPI:
    """Test the cron jobs configuration endpoint"""

    base_uri = "/api/config/workers/cron-jobs"

    def test_get_cron_jobs_returns_expected_structure(self, client, auth_header, osint_sources, bots):
        """Test that the cron-jobs endpoint returns properly structured data"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        assert "cron_jobs" in data
        assert isinstance(data["cron_jobs"], list)

        # Verify the structure of returned jobs
        if data["cron_jobs"]:
            job = data["cron_jobs"][0]
            required_fields = ["task", "queue", "args", "cron", "task_id", "name"]
            for field in required_fields:
                assert field in job, f"Missing required field: {field}"

    def test_get_cron_jobs_includes_enabled_osint_sources(self, client, auth_header, osint_sources):
        """Test that enabled OSINT sources with schedules are included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        collector_jobs = [job for job in data["cron_jobs"] if job["task"] == "collector_task"]

        # Should have at least one collector job from fixtures
        assert len(collector_jobs) > 0

        # Verify collector job structure
        for job in collector_jobs:
            assert job["queue"] == "collectors"
            assert isinstance(job["args"], list)
            assert len(job["args"]) == 2  # [source_id, False]
            assert job["args"][1] is False  # manual=False
            assert job["cron"]  # Should have a cron schedule
            assert job["task_id"].startswith("collect_")

    def test_get_cron_jobs_includes_enabled_bots(self, client, auth_header, bots):
        """Test that enabled bots with schedules are included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        bot_jobs = [job for job in data["cron_jobs"] if job["task"] == "bot_task"]

        # Should have bot jobs from fixtures
        assert len(bot_jobs) > 0

        # Verify bot job structure
        for job in bot_jobs:
            assert job["queue"] == "bots"
            assert isinstance(job["args"], list)
            assert len(job["args"]) == 1  # [bot_id]
            assert job["cron"]  # Should have a cron schedule
            assert job["task_id"].startswith("bot_")

    def test_get_cron_jobs_includes_housekeeping_tasks(self, client, auth_header):
        """Test that housekeeping tasks are included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        housekeeping_jobs = [job for job in data["cron_jobs"] if job["task"] == "cleanup_token_blacklist"]

        # Should have exactly one cleanup job
        assert len(housekeeping_jobs) == 1

        cleanup_job = housekeeping_jobs[0]
        assert cleanup_job["queue"] == "misc"
        assert cleanup_job["args"] == []
        assert cleanup_job["cron"] == "0 2 * * *"
        assert cleanup_job["task_id"] == "cleanup_token_blacklist"
        assert cleanup_job["name"] == "Cleanup Token Blacklist"

    def test_get_cron_jobs_excludes_disabled_sources(self, client, auth_header, disabled_osint_source):
        """Test that disabled OSINT sources are not included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        # Get the disabled source ID from the fixture
        disabled_id = disabled_osint_source.id

        # Verify no job exists for the disabled source
        collector_jobs = [job for job in data["cron_jobs"] if job["task"] == "collector_task" and disabled_id in str(job["args"])]
        assert len(collector_jobs) == 0

    def test_get_cron_jobs_excludes_disabled_bots(self, client, auth_header, disabled_bot):
        """Test that disabled bots are not included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        # Get the disabled bot ID from the fixture
        disabled_id = disabled_bot.id

        # Verify no job exists for the disabled bot
        bot_jobs = [job for job in data["cron_jobs"] if job["task"] == "bot_task" and disabled_id in job["args"]]
        assert len(bot_jobs) == 0

    def test_get_cron_jobs_excludes_sources_without_schedule(self, client, auth_header, osint_source_no_schedule):
        """Test that OSINT sources without schedules are not included"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        source_id = osint_source_no_schedule.id

        # Verify no job exists for the source without schedule
        collector_jobs = [job for job in data["cron_jobs"] if job["task"] == "collector_task" and source_id in str(job["args"])]
        assert len(collector_jobs) == 0

    def test_get_cron_jobs_requires_authentication(self, client):
        """Test that the endpoint requires authentication"""
        response = client.get(self.base_uri)
        assert response.status_code == 401

    def test_get_cron_jobs_handles_empty_database(self, client, auth_header):
        """Test that the endpoint handles empty database gracefully"""
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200

        data = response.get_json()
        assert "cron_jobs" in data
        # Should at least have housekeeping tasks even if no sources/bots
        housekeeping_jobs = [job for job in data["cron_jobs"] if job["task"] == "cleanup_token_blacklist"]
        assert len(housekeeping_jobs) == 1


class TestWorkerCronJobsAPI:
    """Test the worker cron jobs endpoint (API key auth)"""

    base_uri = "/api/worker/cron-jobs"

    def test_get_cron_jobs_returns_expected_structure(self, client, api_header, osint_sources, bots):
        response = client.get(self.base_uri, headers=api_header)
        assert response.status_code == 200

        data = response.get_json()
        assert "cron_jobs" in data
        assert isinstance(data["cron_jobs"], list)

        if data["cron_jobs"]:
            job = data["cron_jobs"][0]
            required_fields = ["task", "queue", "args", "cron", "task_id", "name"]
            for field in required_fields:
                assert field in job, f"Missing required field: {field}"

    def test_get_cron_jobs_requires_authentication(self, client):
        response = client.get(self.base_uri)
        assert response.status_code == 401
