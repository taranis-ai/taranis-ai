# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false
from datetime import datetime, timezone
from typing import Any, cast

import pytest
import rq.registry as rq_registry

from core.managers import auth_manager
from core.managers import queue_manager as qm_module
from core.managers.queue_manager import QueueManager
from core.model.bot import Bot
from core.model.osint_source import OSINTSource
from core.model.task import Task as TaskModel


@pytest.fixture(autouse=True)
def disable_token_revocation(monkeypatch):
    """Avoid hitting the database for JWT blacklist checks during unit tests."""
    from core.model import token_blacklist

    monkeypatch.setattr(auth_manager, "check_if_token_is_revoked", lambda *_, **__: False)
    monkeypatch.setattr(token_blacklist.TokenBlacklist, "invalid", classmethod(lambda cls, jti: False))


class _FakeRedis:
    def __init__(self):
        self.hashes = {"rq:cron:def": {"job-123": b'{"cron":"0 * * * *"}'}}
        self.zsets = {"rq:cron:next": {"job-123": 1234.0}}
        self.events: list[tuple[str, dict[str, str]]] = []
        self.published: list[tuple[str, str]] = []

    def hexists(self, key, field):
        return field in self.hashes.get(key, {})

    def zscore(self, key, member):
        return self.zsets.get(key, {}).get(member)

    def hkeys(self, key):
        return list(self.hashes.get(key, {}).keys())

    def publish(self, channel, message):
        self.published.append((channel, message))
        return 1

    def pipeline(self):
        redis = self

        class _Pipeline:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def hset(self, key, field, value):
                redis.hashes.setdefault(key, {})[field] = value
                return self

            def hdel(self, key, field):
                redis.hashes.setdefault(key, {}).pop(field, None)
                return self

            def zadd(self, key, mapping):
                redis.zsets.setdefault(key, {}).update(mapping)
                return self

            def zrem(self, key, member):
                redis.zsets.setdefault(key, {}).pop(member, None)
                return self

            def xadd(self, key, values):
                redis.events.append((key, values))
                return self

            def execute(self):
                return True

        return _Pipeline()


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


def test_annotate_jobs_marks_overdue_scheduled(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 10, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "scheduled",
        "next_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "last_run": datetime(2025, 12, 12, 7, 50, 0),
    }

    annotated = qm_module._annotate_jobs([job])[0]

    assert annotated["status_badge"]["variant"] == "warning"
    assert annotated["is_overdue"] is True
    assert annotated["last_run_relative"].endswith("ago")


def test_annotate_jobs_marks_first_cron_run_pending(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 0, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(qm_module, "datetime", _FixedDateTime)

    job = {
        "type": "cron",
        "last_run": None,
        "previous_run_time": datetime(2025, 12, 12, 8, 0, 0),
        "next_run_time": datetime(2025, 12, 12, 10, 0, 0),
    }

    annotated = qm_module._annotate_jobs([job])[0]

    assert annotated["status_badge"]["label"] == "Pending first run"
    assert annotated["is_overdue"] is False


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
    assert qm._redis.hashes["rq:cron:def"] == {}  # type: ignore[attr-defined]
    assert qm._redis.zsets["rq:cron:next"] == {}  # type: ignore[attr-defined]


def test_cancel_job_returns_false_when_not_found(monkeypatch):
    def fake_fetch(job_id, connection=None):
        raise Exception("missing")

    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()
    qm._redis = _FakeRedis()
    qm._redis.hashes["rq:cron:def"] = {}  # type: ignore[attr-defined]
    qm._redis.zsets["rq:cron:next"] = {}  # type: ignore[attr-defined]

    assert qm.cancel_job("job-123") is False


def test_publish_schedule_cache_invalidation_notifies_scheduler_views():
    qm = _make_queue_manager()

    published = qm.publish_schedule_cache_invalidation()

    assert published == 2
    assert qm._redis.published == [  # type: ignore[attr-defined]
        ("taranis:cache:invalidate", "/config/schedule"),
        ("taranis:cache:invalidate", "/config/workers/dashboard"),
    ]


def test_get_active_jobs_uses_registry(monkeypatch):
    class FakeJob:
        def __init__(self, job_id):
            self.id = job_id
            self.func_name = "other.task"
            self.args = []
            self.meta = {}
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
            self.meta = {}
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


def test_get_failed_jobs_removes_stale_registry_entries(monkeypatch):
    removed: list[tuple[str, bool]] = []

    class FakeRegistry:
        def __init__(self, queue=None):
            self.queue = queue

        def get_job_ids(self):
            return ["job-stale"]

        def remove(self, job_id, delete_job=False):
            removed.append((job_id, delete_job))

    def fake_fetch(job_id, connection=None):
        raise qm_module.NoSuchJobError(f"No such job: rq:job:{job_id}")

    monkeypatch.setattr(rq_registry, "FailedJobRegistry", FakeRegistry)
    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()
    qm._queues = {"bots": _DummyQueue("bots")}  # type: ignore[assignment]

    payload, status = qm.get_failed_jobs()

    assert status == 200
    assert payload == {"items": [], "total_count": 0}
    assert removed == [("job-stale", False)]


def test_osint_schedule_entries_include_metadata(monkeypatch):
    class FakeTask:
        def __init__(self):
            self.last_run = datetime(2025, 1, 1, 0, 0, 0)
            self.last_success = datetime(2025, 1, 1, 0, 0, 0)
            self.status = "ok"

    class FakeSource:
        def __init__(self):
            self.id = "source-1"
            self.name = "Source One"
            self.task_id = "task-1"

        def get_schedule(self):
            return "0 * * * *"

        def get_schedule_with_default(self):
            return self.get_schedule()

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [FakeSource()]))
    monkeypatch.setattr(TaskModel, "get", classmethod(lambda cls, task_id: FakeTask() if task_id == "task-1" else None))

    entries = OSINTSource.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries
    entry = entries[0]
    assert entry["id"] == "cron_collector_source-1"
    assert entry["queue"] == "collectors"
    assert entry["previous_run_time"]


def test_osint_schedule_entries_handle_many(monkeypatch):
    def make_source(idx: int):
        class FakeSource:
            def __init__(self, i):
                self.id = f"source-{i}"
                self.name = f"Source {i}"
                self.task_id = f"task-{i}"

            def get_schedule(self):
                return f"*/{(idx % 5) + 1} * * * *"

            def get_schedule_with_default(self):
                return self.get_schedule()

        return FakeSource(idx)

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [make_source(i) for i in range(120)]))
    monkeypatch.setattr(TaskModel, "get", classmethod(lambda cls, task_id: None))

    entries = OSINTSource.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert len(entries) == 120
    assert len({e["id"] for e in entries}) == 120


def test_bot_schedule_entries_skip_invalid_cron(monkeypatch):
    class FakeBot:
        def __init__(self):
            self.id = "bot-1"
            self.name = "Bot One"
            self.task_id = "task-1"

        def get_schedule(self):
            return "not-a-cron"

    monkeypatch.setattr(Bot, "get_all_for_collector", classmethod(lambda cls: [FakeBot()]))
    monkeypatch.setattr(TaskModel, "get", classmethod(lambda cls, task_id: None))

    entries = Bot.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries == []


def test_get_scheduled_jobs_with_many_sources(monkeypatch):
    def fake_osint_entries():
        return [
            {
                "id": f"cron_collector_{i}",
                "name": f"Collector {i}",
                "queue": "collectors",
                "next_run_time": datetime(2025, 1, 1, 0, 0, 0),
                "previous_run_time": datetime(2024, 12, 31, 23, 0, 0),
                "schedule": "0 * * * *",
                "type": "cron",
                "last_run": None,
                "last_success": None,
                "last_status": None,
            }
            for i in range(120)
        ]

    monkeypatch.setattr(OSINTSource, "get_enabled_schedule_entries", classmethod(lambda cls: fake_osint_entries()))
    monkeypatch.setattr(Bot, "get_enabled_schedule_entries", classmethod(lambda cls: []))

    qm = _make_queue_manager()
    qm._redis = object()

    schedules, status = qm.get_scheduled_jobs()

    assert status == 200
    # 120 OSINT cron jobs + housekeeping cleanup cron
    assert schedules["total_count"] == 121


def test_reschedule_all_prunes_stale_managed_cron_jobs(monkeypatch):
    class FakeSpec:
        def __init__(self, job_id: str, task_name: str, queue_name: str):
            self.job_id = job_id
            self.task_name = task_name
            self.queue_name = queue_name
            self.cron = "0 * * * *"
            self.interval = None

        def model_dump(self, mode="json"):
            del mode
            return {
                "job_id": self.job_id,
                "func_path": self.task_name,
                "queue_name": self.queue_name,
                "cron": self.cron,
                "args": [],
                "kwargs": {},
                "job_options": {},
                "meta": {},
            }

    class FakeSource:
        enabled = True

        def __init__(self, source_id: str):
            self.id = source_id

        def get_schedule_with_default(self):
            return "0 * * * *"

        def get_cron_spec(self):
            return FakeSpec(f"osint_source_{self.id}", "collector_task", "collectors")

    class FakeBot:
        enabled = True

        def __init__(self, bot_id: str):
            self.id = bot_id

        def get_schedule(self):
            return "0 * * * *"

        def get_cron_spec(self):
            return FakeSpec(f"bot_{self.id}", "bot_task", "bots")

    qm = _make_queue_manager()
    qm._queues = {"collectors": _DummyQueue("collectors"), "bots": _DummyQueue("bots")}  # type: ignore[assignment]
    qm._redis.hashes["rq:cron:def"] = {  # type: ignore[attr-defined]
        "osint_source_stale": b'{"cron":"0 * * * *"}',
        "bot_stale": b'{"cron":"0 * * * *"}',
        "custom_keep": b'{"cron":"0 * * * *"}',
    }
    qm._redis.zsets["rq:cron:next"] = {  # type: ignore[attr-defined]
        "osint_source_stale": 1234.0,
        "bot_stale": 1234.0,
        "custom_keep": 1234.0,
    }

    purged_calls: list[tuple[set[str], list[str]]] = []

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [FakeSource("live-source")]))
    monkeypatch.setattr(Bot, "get_all_for_collector", classmethod(lambda cls: [FakeBot("live-bot")]))
    monkeypatch.setattr(
        qm,
        "purge_job_artifacts",
        lambda *, exact_ids=None, prefixes=None: purged_calls.append((exact_ids or set(), prefixes or [])) or (3, 2),
    )

    qm.reschedule_all()

    assert "osint_source_live-source" in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "bot_live-bot" in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "osint_source_stale" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "bot_stale" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "custom_keep" in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert len(purged_calls) == 1
    assert purged_calls[0][0] == set()
    assert set(purged_calls[0][1]) == {"cron_osint_source_stale_", "cron_bot_stale_"}
