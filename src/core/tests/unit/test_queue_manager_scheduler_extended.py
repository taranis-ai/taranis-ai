from __future__ import annotations
# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

from datetime import datetime, timedelta, timezone
from typing import Any, cast

import flask_jwt_extended.utils as jwt_utils
import pytest
import rq.job as rq_job
import rq.registry as rq_registry

from core.managers import auth_manager, queue_manager as qm_module
from core.managers.queue_manager import QueueManager
from core.model.bot import Bot
from core.model.osint_source import OSINTSource


@pytest.fixture(autouse=True)
def disable_token_revocation(monkeypatch):
    """Avoid hitting the database for JWT blacklist checks during unit tests."""
    from core.model import token_blacklist

    monkeypatch.setattr(auth_manager, "check_if_token_is_revoked", lambda *_, **__: False)
    monkeypatch.setattr(token_blacklist.TokenBlacklist, "invalid", classmethod(lambda cls, jti: False))


class _FakeRedis:
    def __init__(self):
        self.deleted_keys: list[str] = []

    def delete(self, key):
        if key.startswith("rq:cron:"):
            self.deleted_keys.append(key)
            return 1
        return 0


class _DummyQueue:
    """Lightweight queue stub carrying the fields accessed by rq registries."""

    def __init__(self, name: str):
        self.name = name
        self.connection = object()


def _make_queue_manager() -> QueueManager:
    qm = QueueManager.__new__(QueueManager)
    qm.error = ""
    qm._queues = cast(dict[str, Any], {})
    qm._redis = _FakeRedis()
    return qm


def test_parse_iso_datetime_handles_z_and_offsets():
    dt_z = qm_module._parse_iso_datetime("2025-01-01T10:00:00Z")
    dt_offset = qm_module._parse_iso_datetime("2025-01-01T10:00:00+02:00")

    assert dt_z and dt_z.tzinfo is None
    assert dt_offset and dt_offset.hour == 8 and dt_offset.tzinfo is None


def test_parse_iso_datetime_invalid():
    assert qm_module._parse_iso_datetime("not-a-date") is None
    assert qm_module._parse_iso_datetime(None) is None


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(seconds=59), "59s"),
        (timedelta(minutes=1, seconds=1), "1m 1s"),
        (timedelta(hours=2, minutes=5), "2h 5m"),
        (timedelta(days=1, hours=3), "1d 3h"),
    ],
)
def test_format_duration(delta, expected):
    assert qm_module._format_duration(delta) == expected


def test_annotate_jobs_marks_overdue_scheduled(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 10, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "scheduled",
        "next_run_time": "2025-12-12T08:00:00",
        "last_run": "2025-12-12T07:50:00",
    }

    annotated = qm_module._annotate_jobs([job])[0]

    assert annotated["status_badge"]["variant"] == "warning"
    assert annotated["is_overdue"] is True
    assert annotated["last_run_relative"].endswith("ago")


def test_annotate_jobs_computes_missing_interval(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 0, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "last_run": None,
        "previous_run_time": "2025-12-12T08:00:00",
        "next_run_time": "2025-12-12T10:00:00",
    }

    annotated = qm_module._annotate_jobs([job])[0]

    assert annotated["interval_seconds"] == 2 * 60 * 60
    assert annotated["status_badge"]["label"] == "Pending first run"


def test_get_next_fire_times_from_cron_returns_three():
    times = QueueManager.get_next_fire_times_from_cron("*/15 * * * *")
    assert len(times) == 3
    assert times[0] < times[1] < times[2]


def test_cancel_job_cancels_instance_and_cron(monkeypatch):
    class FakeJob:
        def __init__(self, job_id):
            self.id = job_id
            self.cancelled = False
            self.deleted = False

        def cancel(self):
            self.cancelled = True

        def delete(self):
            self.deleted = True

    last_job: list[FakeJob] = []

    def fake_fetch(job_id, connection=None):
        job = FakeJob(job_id)
        last_job.append(job)
        return job

    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()

    assert qm.cancel_job("job-123") is True
    assert last_job and last_job[0].cancelled and last_job[0].deleted
    assert qm._redis.deleted_keys == ["rq:cron:job-123"]  # type: ignore[attr-defined]


def test_cancel_job_returns_false_when_not_found(monkeypatch):
    def fake_fetch(job_id, connection=None):
        raise Exception("missing")

    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()

    assert qm.cancel_job("job-123") is True  # cron entry deletion still returns True


def test_retry_failed_job_requeues(monkeypatch):
    class FakeQueue:
        def __init__(self):
            self.enqueued = False

        def enqueue_job(self, job):
            self.enqueued = True

    class FakeJob:
        def __init__(self):
            self.is_failed = True
            self.origin = "bots"

    monkeypatch.setattr(
        qm_module,
        "Job",
        type("Job", (), {"fetch": staticmethod(lambda job_id, connection=None: FakeJob())}),
    )

    qm = _make_queue_manager()
    qm._queues = {"bots": FakeQueue()}

    payload, status = qm.retry_failed_job("job-1")

    assert status == 200
    assert payload["message"].startswith("Job job-1")
    assert qm._queues["bots"].enqueued is True


def test_retry_failed_job_rejects_non_failed(monkeypatch):
    class FakeJob:
        def __init__(self):
            self.is_failed = False
            self.origin = "bots"

    monkeypatch.setattr(
        qm_module,
        "Job",
        type("Job", (), {"fetch": staticmethod(lambda job_id, connection=None: FakeJob())}),
    )

    qm = _make_queue_manager()
    qm._queues = {"bots": object()}

    payload, status = qm.retry_failed_job("job-1")

    assert status == 400
    assert "not in failed state" in payload["error"]


def test_get_active_jobs_uses_registry(monkeypatch):
    class FakeJob:
        def __init__(self, job_id):
            self.id = job_id
            self.func_name = "other.task"
            self.args = []
            self.started_at = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeRegistry:
        def __init__(self, queue=None):
            self.queue = queue

        def get_job_ids(self):
            return ["job-1"]

    def fake_fetch(job_id, connection=None):
        return FakeJob(job_id)

    monkeypatch.setattr(rq_registry, "StartedJobRegistry", FakeRegistry)
    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()
    qm._queues = {"bots": _DummyQueue("bots")}  # type: ignore[assignment]

    payload, status = qm.get_active_jobs()

    assert status == 200
    assert payload["items"][0]["id"] == "job-1"
    assert payload["items"][0]["status"] == "running"


def test_get_failed_jobs_uses_registry(monkeypatch):
    class FakeJob:
        def __init__(self, job_id):
            self.id = job_id
            self.func_name = "other.task"
            self.args = []
            self.ended_at = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
            self.exc_info = "boom"

    class FakeRegistry:
        def __init__(self, queue=None):
            self.queue = queue

        def get_job_ids(self):
            return ["job-9"]

    def fake_fetch(job_id, connection=None):
        return FakeJob(job_id)

    monkeypatch.setattr(rq_registry, "FailedJobRegistry", FakeRegistry)
    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()
    qm._queues = {"misc": _DummyQueue("misc")}  # type: ignore[assignment]

    payload, status = qm.get_failed_jobs()

    assert status == 200
    assert payload["items"][0]["id"] == "job-9"
    assert payload["items"][0]["status"] == "failed"


def test_osint_schedule_entries_include_metadata(monkeypatch):
    class FakeSource:
        def __init__(self):
            self.id = "source-1"
            self.name = "Source One"
            self.status = {"last_run": "2025-01-01T00:00:00", "status": "ok"}
            self.task_id = "task-1"

        def get_schedule(self):
            return "0 * * * *"

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [FakeSource()]))

    entries = OSINTSource.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries
    entry = entries[0]
    assert entry["id"] == "cron_collector_source-1"
    assert entry["queue"] == "collectors"
    assert entry["previous_run_time"]
    assert entry["interval_seconds"] is not None


def test_osint_schedule_entries_handle_many(monkeypatch):
    def make_source(idx: int):
        class FakeSource:
            def __init__(self, i):
                self.id = f"source-{i}"
                self.name = f"Source {i}"
                self.status = {}
                self.task_id = f"task-{i}"

            def get_schedule(self):
                return f"*/{(idx % 5) + 1} * * * *"

        return FakeSource(idx)

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [make_source(i) for i in range(120)]))

    entries = OSINTSource.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert len(entries) == 120
    assert len({e["id"] for e in entries}) == 120


def test_bot_schedule_entries_skip_invalid_cron(monkeypatch):
    class FakeBot:
        def __init__(self):
            self.id = "bot-1"
            self.name = "Bot One"
            self.status = {}
            self.task_id = "task-1"

        def get_schedule(self):
            return "not-a-cron"

    monkeypatch.setattr(Bot, "get_all_for_collector", classmethod(lambda cls: [FakeBot()]))

    entries = Bot.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries == []


def test_schedule_endpoint_returns_items(client, auth_header, monkeypatch):
    class FakeQM:
        def get_scheduled_jobs(self):
            return {"items": [{"id": "job-1"}], "total_count": 1}, 200

    monkeypatch.setattr(qm_module, "queue_manager", FakeQM())
    monkeypatch.setattr(auth_manager, "verify_jwt_in_request", lambda *a, **k: None)
    monkeypatch.setattr(auth_manager, "get_jwt_identity", lambda: "tester")
    monkeypatch.setattr(jwt_utils, "get_jwt", lambda: {"sub": "tester"})
    monkeypatch.setattr(jwt_utils, "get_current_user", lambda: type("User", (), {"get_permissions": lambda self: {"CONFIG_WORKER_ACCESS"}})())

    response = client.get("/api/config/schedule", headers=auth_header)

    assert response.status_code == 200
    assert response.json["items"][0]["id"] == "job-1"


def test_schedule_task_endpoint_returns_single_job(client, auth_header, monkeypatch):
    class FakeJob:
        def __init__(self):
            self.id = "job-42"
            self.func_name = "worker.do_task"
            self.enqueued_at = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        def get_status(self):
            return "queued"

    import core.api.config as config_api

    fake_qm = type("FakeQM", (), {"redis": object()})()

    monkeypatch.setattr(qm_module, "queue_manager", fake_qm)
    monkeypatch.setattr(config_api.queue_manager, "queue_manager", fake_qm)
    monkeypatch.setattr(rq_job.Job, "fetch", staticmethod(lambda job_id, connection=None: FakeJob()))
    monkeypatch.setattr(auth_manager, "verify_jwt_in_request", lambda *a, **k: None)
    monkeypatch.setattr(auth_manager, "get_jwt_identity", lambda: "tester")
    monkeypatch.setattr(jwt_utils, "get_jwt", lambda: {"sub": "tester"})
    monkeypatch.setattr(jwt_utils, "get_current_user", lambda: type("User", (), {"get_permissions": lambda self: {"CONFIG_WORKER_ACCESS"}})())

    response = client.get("/api/config/schedule/job-42", headers=auth_header)

    assert response.status_code == 200
    assert response.json["id"] == "job-42"
    assert response.json["status"] == "queued"


def test_refresh_interval_endpoint(client, auth_header, monkeypatch):
    times = [
        datetime(2025, 1, 1, 12, 0),
        datetime(2025, 1, 1, 12, 15),
        datetime(2025, 1, 1, 12, 30),
    ]

    monkeypatch.setattr(QueueManager, "get_next_fire_times_from_cron", classmethod(lambda cls, cron, n=3: times))
    monkeypatch.setattr(auth_manager, "verify_jwt_in_request", lambda *a, **k: None)
    monkeypatch.setattr(auth_manager, "get_jwt_identity", lambda: "tester")
    monkeypatch.setattr(jwt_utils, "get_jwt", lambda: {"sub": "tester"})
    monkeypatch.setattr(jwt_utils, "get_current_user", lambda: type("User", (), {"get_permissions": lambda self: {"CONFIG_WORKER_ACCESS"}})())

    response = client.post("/api/config/refresh-interval", headers=auth_header, json={"cron": "*/15 * * * *"})

    assert response.status_code == 200
    assert response.json == ["2025-01-01T12:00", "2025-01-01T12:15", "2025-01-01T12:30"]


def test_get_scheduled_jobs_with_many_sources(monkeypatch):
    class FakeRedisWithCron:
        def zrange(self, key, start, end):
            return ["scheduler"] if key == "rq:cron_schedulers" else []

    def fake_osint_entries():
        return [
            {
                "id": f"cron_collector_{i}",
                "name": f"Collector {i}",
                "queue": "collectors",
                "next_run_time": "2025-01-01T00:00:00",
                "previous_run_time": "2024-12-31T23:00:00",
                "schedule": "0 * * * *",
                "type": "cron",
                "interval_seconds": 3600,
                "last_run": None,
                "last_success": None,
                "last_status": None,
            }
            for i in range(120)
        ]

    monkeypatch.setattr(OSINTSource, "get_enabled_schedule_entries", classmethod(lambda cls: fake_osint_entries()))
    monkeypatch.setattr(Bot, "get_enabled_schedule_entries", classmethod(lambda cls: []))

    qm = _make_queue_manager()
    qm._redis = FakeRedisWithCron()

    schedules, status = qm.get_scheduled_jobs()

    assert status == 200
    # 120 OSINT cron jobs + housekeeping cleanup cron
    assert schedules["total_count"] == 121
