import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import cast

from redis import Redis
from rq import Queue

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
    queue_manager._redis = cast(Redis, object())

    with app.app_context():
        schedules, status = QueueManager.get_scheduled_jobs(queue_manager, {})

    assert status == 200
    items = schedules.get("items", [])
    cleanup_jobs = {job.get("id"): job for job in items if job.get("id") in {"cleanup_token_blacklist", "cleanup_task_history"}}
    assert cleanup_jobs.keys() == {"cleanup_token_blacklist", "cleanup_task_history"}

    token_cleanup_job = cleanup_jobs["cleanup_token_blacklist"]
    assert token_cleanup_job.get("queue") == "misc"
    assert token_cleanup_job.get("schedule") == "0 2 * * *"
    assert token_cleanup_job.get("type") == "cron"
    assert isinstance(token_cleanup_job.get("next_run_time"), str)

    history_cleanup_job = cleanup_jobs["cleanup_task_history"]
    assert history_cleanup_job.get("queue") == "misc"
    assert history_cleanup_job.get("schedule") == "0 3 * * *"
    assert history_cleanup_job.get("type") == "cron"
    assert isinstance(history_cleanup_job.get("next_run_time"), str)


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
    queue_manager._queues = cast(dict[str, Queue], {"bots": object()})
    queue_manager._redis = cast(Redis, object())

    with caplog.at_level(logging.DEBUG):
        schedules, status = QueueManager.get_scheduled_jobs(queue_manager, {})

    assert status == 200
    assert schedules["total_count"] == 0
    assert "Queue bots: found 0 scheduled jobs in registry" not in caplog.text


def test_annotate_jobs_does_not_mark_late_cron_runs_as_missed(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 12, 40, tzinfo=UTC)

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
    assert annotated_job["last_run_display"] == "2025-12-11 15:51:07 UTC"
    assert annotated_job["next_run_display"] == "2025-12-12 16:00:00 UTC"


def test_annotate_jobs_does_not_mark_future_slot(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=UTC)

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
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=UTC)

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
    assert annotated_job["last_run_display"] is None
    assert annotated_job["next_run_display"] == "2025-12-12 16:00:00 UTC"


def test_annotate_jobs_ignores_many_missed_cron_slots(monkeypatch):
    fixed_now = datetime(2026, 4, 29, 10, 34, 4, tzinfo=UTC)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # pragma: no cover - helper for monkeypatch
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "schedule": "* * * * *",
        "last_run": datetime(2026, 4, 29, 10, 23, 19),
        "previous_run_time": datetime(2026, 4, 29, 10, 34, 0),
        "next_run_time": datetime(2026, 4, 29, 10, 35, 0),
    }

    annotated_job = qm_module._annotate_jobs([job])[0]

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending"
    assert annotated_job["is_overdue"] is False


def test_annotate_jobs_normalizes_aware_timestamps_to_utc(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 12, 40, tzinfo=UTC)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # pragma: no cover - helper for monkeypatch
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    plus_two = timezone(timedelta(hours=2))
    job = {
        "type": "scheduled",
        "last_run": datetime(2025, 12, 12, 14, 30, 0, tzinfo=plus_two),
        "next_run_time": datetime(2025, 12, 12, 14, 45, 0, tzinfo=plus_two),
    }

    annotated_job = qm_module._annotate_jobs([job])[0]

    assert annotated_job["last_run"] == datetime(2025, 12, 12, 12, 30, 0)
    assert annotated_job["next_run_time"] == datetime(2025, 12, 12, 12, 45, 0)
    assert annotated_job["last_run_display"] == "2025-12-12 12:30:00 UTC"
    assert annotated_job["next_run_display"] == "2025-12-12 12:45:00 UTC"
    assert annotated_job["next_run_relative"] == "in 5m"
