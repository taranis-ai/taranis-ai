import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from unittest.mock import Mock

import pytest
from models.scheduler import ScheduledJob
from redis import Redis
from redis.exceptions import ConnectionError
from rq import Queue

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


def test_annotate_jobs_does_not_mark_late_cron_runs_as_missed():
    fixed_now = datetime(2025, 12, 12, 12, 40, tzinfo=UTC)

    job = {
        "type": "cron",
        "last_run": datetime(2025, 12, 11, 15, 51, 7),
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = ScheduledJob.model_validate(job).model_dump(context={"now": fixed_now.replace(tzinfo=None)})

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending"
    assert annotated_job["last_run_display"] == "2025-12-11 15:51:07 UTC"
    assert annotated_job["next_run_display"] == "2025-12-12 16:00:00 UTC"


def test_annotate_jobs_does_not_mark_future_slot():
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=UTC)

    job = {
        "type": "cron",
        "last_run": datetime(2025, 12, 11, 15, 51, 7),
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = ScheduledJob.model_validate(job).model_dump(context={"now": fixed_now.replace(tzinfo=None)})

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending"


def test_annotate_jobs_pending_first_run():
    fixed_now = datetime(2025, 12, 12, 7, 59, tzinfo=UTC)

    job = {
        "type": "cron",
        "last_run": None,
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 16, 0, 0),
    }

    annotated_job = ScheduledJob.model_validate(job).model_dump(context={"now": fixed_now.replace(tzinfo=None)})

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending first run"
    assert not annotated_job["is_overdue"]
    assert annotated_job["last_run_display"] is None
    assert annotated_job["next_run_display"] == "2025-12-12 16:00:00 UTC"


def test_annotate_jobs_ignores_many_missed_cron_slots():
    fixed_now = datetime(2026, 4, 29, 10, 34, 4, tzinfo=UTC)

    job = {
        "type": "cron",
        "schedule": "* * * * *",
        "last_run": datetime(2026, 4, 29, 10, 23, 19),
        "previous_run_time": datetime(2026, 4, 29, 10, 34, 0),
        "next_run_time": datetime(2026, 4, 29, 10, 35, 0),
    }

    annotated_job = ScheduledJob.model_validate(job).model_dump(context={"now": fixed_now.replace(tzinfo=None)})

    assert annotated_job["status_badge"]["variant"] == "ghost"
    assert annotated_job["status_badge"]["label"] == "Pending"
    assert annotated_job["is_overdue"] is False


def test_annotate_jobs_normalizes_aware_timestamps_to_utc():
    fixed_now = datetime(2025, 12, 12, 12, 40, tzinfo=UTC)

    plus_two = timezone(timedelta(hours=2))
    job = {
        "type": "scheduled",
        "last_run": datetime(2025, 12, 12, 14, 30, 0, tzinfo=plus_two),
        "next_run_time": datetime(2025, 12, 12, 14, 45, 0, tzinfo=plus_two),
    }

    annotated_job = ScheduledJob.model_validate(job).model_dump(context={"now": fixed_now.replace(tzinfo=None)})

    assert annotated_job["last_run"] == datetime(2025, 12, 12, 12, 30, 0)
    assert annotated_job["next_run_time"] == datetime(2025, 12, 12, 12, 45, 0)
    assert annotated_job["last_run_display"] == "2025-12-12 12:30:00 UTC"
    assert annotated_job["next_run_display"] == "2025-12-12 12:45:00 UTC"
    assert annotated_job["next_run_relative"] == "in 5m"


@pytest.mark.parametrize("queue_enabled", [False, True])
def test_core_startup_without_redis_requires_explicit_queue_disable(app, auth_header, monkeypatch, queue_enabled):
    from core import create_app
    from core.config import Config
    from core.managers import queue_manager
    from core.service.cache_invalidation import FrontendCacheInvalidationService

    monkeypatch.setattr(Config, "QUEUE_ENABLED", queue_enabled)
    monkeypatch.setattr(Config, "CACHE_ENABLED", True)
    monkeypatch.setattr(Config, "CACHE_REDIS_URL", None)
    monkeypatch.setattr(queue_manager, "queue_manager", queue_manager.queue_manager)
    connect = Mock(side_effect=ConnectionError("Redis unavailable"))
    monkeypatch.setattr("redis.Redis.from_url", connect)

    if queue_enabled:
        with pytest.raises(ConnectionError):
            create_app(initial_setup=False)
        connect.assert_called_once()
        return

    disabled_app = create_app(initial_setup=False)
    manager = disabled_app.extensions["rq"]
    manager.post_init()
    assert manager.redis is None
    assert manager.enqueue_task("misc", "gather_word_list", "test") is False
    assert manager.get_scheduled_job("missing")[1] == 503
    assert FrontendCacheInvalidationService()._get_client() is None

    client = disabled_app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["services"]["broker"] == "n/a"
    assert response.json["services"]["workers"] == "n/a"
    response = client.post("/api/config/word-lists/gather/test", headers=auth_header)
    assert response.status_code == 503
    assert response.json == {"error": "Queue is disabled"}
    for path in (
        "/api/config/osint-sources/missing/collect",
        "/api/config/osint-sources/missing/preview",
        "/api/config/bots/missing/execute",
    ):
        response = client.post(path, headers=auth_header)
        assert response.status_code == 503
        assert response.json == {"error": "Queue is disabled"}
    assert manager.execute_bot_task("invalid.id") == ({"error": "Queue is disabled"}, 503)
    assert manager.collect_osint_source("missing", "missing") == ({"error": "Queue is disabled"}, 503)
    assert manager.post_collection_bots("missing") == ({"error": "Queue is disabled"}, 503)
    assert manager.schedule_bot_dependents("missing") == ({"error": "Queue is disabled"}, 503)

    with disabled_app.app_context():
        from core.managers.db_manager import db
        from core.model.osint_source import OSINTSourceGroup

        curated_list = OSINTSource.get_curated_catalog().lists[0]
        source_ids = set(db.session.scalars(db.select(OSINTSource.id)))
        group_ids = set(db.session.scalars(db.select(OSINTSourceGroup.id)))
        try:
            response = client.post(
                "/api/config/curated-osint-source-lists",
                json={"list_names": [curated_list.name]},
                headers=auth_header,
            )
            assert response.status_code == 200
            group = db.session.execute(db.select(OSINTSourceGroup).filter_by(name=curated_list.name)).scalar_one()
            assert {source.name for source in group.osint_sources} == set(curated_list.sources)
        finally:
            for source in db.session.scalars(db.select(OSINTSource).where(OSINTSource.id.not_in(source_ids))):
                db.session.delete(source)
            for group in db.session.scalars(db.select(OSINTSourceGroup).where(OSINTSourceGroup.id.not_in(group_ids))):
                db.session.delete(group)
            db.session.commit()
    connect.assert_not_called()
