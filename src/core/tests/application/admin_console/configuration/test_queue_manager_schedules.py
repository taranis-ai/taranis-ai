import logging
from datetime import datetime, timezone

from core.managers import queue_manager as qm_module
from core.managers.queue_manager import QueueManager
from core.model.bot import Bot
from core.model.osint_source import OSINTSource


def test_get_scheduled_jobs_includes_cleanup_cron(app, monkeypatch):
    monkeypatch.setattr(OSINTSource, "get_enabled_schedule_entries", classmethod(lambda cls: []))
    monkeypatch.setattr(Bot, "get_enabled_schedule_entries", classmethod(lambda cls: []))

    queue_manager = QueueManager.__new__(QueueManager)
    queue_manager.error = ""
    queue_manager._queues = {}
    queue_manager._redis = object()

    with app.app_context():
        schedules, status = QueueManager.get_scheduled_jobs(queue_manager)

    assert status == 200
    items = schedules.get("items", [])
    cleanup_jobs = [job for job in items if job.get("id") == "cleanup_token_blacklist"]
    assert cleanup_jobs, "expected cleanup cron job to be listed"
    cleanup_job = cleanup_jobs[0]
    assert cleanup_job.get("queue") == "misc"
    assert cleanup_job.get("schedule") == "0 2 * * *"
    assert cleanup_job.get("type") == "cron"
    assert isinstance(cleanup_job.get("next_run_time"), str)


def test_get_scheduled_jobs_skips_zero_count_registry_debug_logs(monkeypatch, caplog):
    class FakeRegistry:
        def __init__(self, queue):
            self.queue = queue

        def get_job_ids(self):
            return []

    import rq.registry as rq_registry

    monkeypatch.setattr(rq_registry, "ScheduledJobRegistry", FakeRegistry)
    monkeypatch.setattr(QueueManager, "_get_cron_schedule_entries", lambda self: [])

    queue_manager = QueueManager.__new__(QueueManager)
    queue_manager.error = ""
    queue_manager._queues = {"bots": object()}
    queue_manager._redis = object()

    with caplog.at_level(logging.DEBUG):
        schedules, status = QueueManager.get_scheduled_jobs(queue_manager)

    assert status == 200
    assert schedules["total_count"] == 0
    assert "Queue bots: found 0 scheduled jobs in registry" not in caplog.text


def test_annotate_jobs_uses_previous_run_for_overdue(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 12, 40, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # pragma: no cover - helper for monkeypatch
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "last_run": datetime(2025, 12, 11, 15, 51, 7),
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = qm_module._annotate_jobs([job])[0]

    assert annotated_job["status_badge"]["variant"] == "error"
    assert annotated_job["status_badge"]["label"] == "Missed"


def test_annotate_jobs_does_not_mark_future_slot(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # pragma: no cover - helper for monkeypatch
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "last_run": datetime(2025, 12, 11, 15, 51, 7),
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = qm_module._annotate_jobs([job])[0]

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending"


def test_annotate_jobs_pending_first_run(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # pragma: no cover - helper for monkeypatch
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "last_run": None,
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = qm_module._annotate_jobs([job])[0]

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending first run"
    assert not annotated_job["is_overdue"]
