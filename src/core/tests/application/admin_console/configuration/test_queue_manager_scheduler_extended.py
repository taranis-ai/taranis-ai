# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import fakeredis
import pytest
import rq.registry as rq_registry
from rq import Queue

import core.service.dashboard as dashboard_module
from core.managers import queue_manager as qm_module
from core.managers.queue_manager import QueueManager
from core.model.bot import Bot
from core.model.osint_source import OSINTSource
from core.model.task import Task as TaskModel
from core.service.dashboard import DashboardService
from tests.application.support.builders import create_osint_source


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


class _FailedResult:
    exc_string = "Traceback (most recent call last):\nValueError: boom"


class _FailedJob:
    def __init__(self, job_id):
        self.id = job_id
        self.func_name = "other.task"
        self.args = []
        self.meta = {}
        self.ended_at = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)

    @staticmethod
    def latest_result():
        return _FailedResult()


def _make_queue_manager() -> QueueManager:
    qm = QueueManager.__new__(QueueManager)
    qm.error = ""
    qm._queues = cast(dict[str, Any], {})
    qm._redis = _FakeRedis()
    return qm


def test_get_scheduled_job_count_includes_configured_and_housekeeping_jobs(monkeypatch):
    qm = _make_queue_manager()
    monkeypatch.setattr(
        qm,
        "_get_managed_cron_specs",
        lambda: {
            "collector-source-1": None,
            qm_module.TASK_HISTORY_CLEANUP_JOB_ID: None,
            qm_module.TOKEN_CLEANUP_JOB_ID: None,
        },
    )

    assert qm.get_scheduled_job_count() == 3


def test_dashboard_schedule_count_matches_scheduled_jobs_total_for_configured_sources(app, session, monkeypatch):
    qm = _make_queue_manager()
    monkeypatch.setattr(qm_module, "queue_manager", qm)
    monkeypatch.setattr(dashboard_module, "get_health_response", lambda: ({"healthy": True}, 200))

    with app.app_context():
        create_osint_source(rank=1, name="Scheduled count consistency source")

        schedules, status = qm.get_scheduled_jobs({})
        dashboard = DashboardService.get_dashboard_data()["items"][0]

    assert status == 200
    assert dashboard["schedule_length"] > len(qm._get_housekeeping_cron_specs())
    assert dashboard["schedule_length"] == schedules["total_count"]


@pytest.mark.parametrize(
    "filter_args",
    [
        {"page": "invalid", "limit": "invalid"},
        {"page": "0", "limit": "0"},
        {"page": "-2", "limit": "-5"},
    ],
)
def test_filter_sort_paginate_jobs_uses_defaults_for_invalid_paging(filter_args):
    jobs = [{"id": f"job-{index:02d}"} for index in range(25)]

    result = qm_module._filter_sort_paginate_jobs(jobs, filter_args, default_order="id_asc")

    assert [job["id"] for job in result["items"]] == [f"job-{index:02d}" for index in range(20)]
    assert result["total_count"] == 25


def test_annotate_jobs_ignores_scheduled_lateness(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 10, tzinfo=UTC)

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

    assert annotated["status_badge"]["variant"] == "ghost"
    assert annotated["is_overdue"] is False
    assert annotated["last_run_relative"].endswith("ago")


def test_annotate_jobs_marks_first_cron_run_pending(monkeypatch):
    fixed_now = datetime(2025, 12, 12, 8, 0, tzinfo=UTC)

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


def test_annotate_jobs_marks_completed_cron_run_on_schedule():
    job = {
        "type": "cron",
        "last_run": datetime(2025, 12, 12, 8, 0, 0),
        "previous_run_time": datetime(2025, 12, 12, 7, 0, 0),
    }

    annotated = qm_module._annotate_jobs([job])[0]

    assert annotated["status_badge"] == {"variant": "success", "label": "On schedule"}


def test_task_result_reason_ignores_invalid_json():
    task = cast(Any, type("FakeTask", (), {"result": "{not json"})())

    assert qm_module._task_result_reason(task) is None


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


def test_publish_schedule_cache_invalidation_notifies_scheduler_views(monkeypatch):
    qm = _make_queue_manager()
    cache_invalidation_calls: list[str] = []

    def fake_invalidate_scope(scope_name: str) -> int:
        cache_invalidation_calls.append(scope_name)
        return 2

    from core.service import cache_invalidation as cache_invalidation_module

    monkeypatch.setattr(cache_invalidation_module.cache_invalidation_service, "invalidate_scope", fake_invalidate_scope)

    published = qm.publish_schedule_cache_invalidation()

    assert published == 2
    assert cache_invalidation_calls == ["schedule"]


def test_get_task_returns_live_rq_status(monkeypatch):
    class FakeJob:
        id = "source_preview_123"
        is_finished = False
        is_failed = False

        @staticmethod
        def get_status():
            return "STARTED"

    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(lambda task_id, connection=None: FakeJob())}))

    qm = _make_queue_manager()

    response, status = qm.get_task("source_preview_123")

    assert status == 202
    assert response == {"id": "source_preview_123", "status": "STARTED"}


def test_get_task_returns_success_payload(monkeypatch):
    class FakeJob:
        id = "source_preview_123"
        is_finished = True
        is_failed = False
        result = [{"title": "Preview item"}]

        @staticmethod
        def get_status():
            return "FINISHED"

    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(lambda task_id, connection=None: FakeJob())}))

    qm = _make_queue_manager()

    response, status = qm.get_task("source_preview_123")

    assert status == 200
    assert response == {"id": "source_preview_123", "status": "SUCCESS", "result": [{"title": "Preview item"}]}


def test_preview_osint_source_purges_existing_preview_artifacts(monkeypatch):
    purged_calls: list[tuple[set[str], list[str]]] = []

    class FakeJob:
        id = "source_preview_123"

    qm = _make_queue_manager()
    monkeypatch.setattr(
        qm,
        "purge_job_artifacts",
        lambda *, exact_ids=None, prefixes=None: purged_calls.append((exact_ids or set(), prefixes or [])) or (1, 1),
    )
    monkeypatch.setattr(qm, "enqueue_task", lambda *args, **kwargs: FakeJob())

    response, status = qm.preview_osint_source("123")

    assert purged_calls == [({"source_preview_123"}, [])]
    assert status == 201
    assert response == {"message": "Preview for source scheduled", "id": "source_preview_123", "status": "STARTED"}


def test_get_active_jobs_uses_registry(monkeypatch):
    class FakeJob:
        def __init__(self, job_id):
            self.id = job_id
            self.func_name = "other.task"
            self.args = []
            self.meta = {}
            self.started_at = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)

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

    payload, status = qm.get_active_jobs({})

    assert status == 200
    assert payload["items"][0]["id"] == "job-1"
    assert payload["items"][0]["status"] == "running"


def test_get_failed_jobs_uses_registry(monkeypatch):
    class FakeRegistry:
        def __init__(self, queue=None):
            self.queue = queue

        def get_job_ids(self):
            return ["job-9"]

    def fake_fetch(job_id, connection=None):
        return _FailedJob(job_id)

    monkeypatch.setattr(rq_registry, "FailedJobRegistry", FakeRegistry)
    monkeypatch.setattr(qm_module, "Job", type("Job", (), {"fetch": staticmethod(fake_fetch)}))

    qm = _make_queue_manager()
    qm._queues = {"misc": _DummyQueue("misc")}  # type: ignore[assignment]

    payload, status = qm.get_failed_jobs({})

    assert status == 200
    assert payload["items"][0]["id"] == "job-9"
    assert payload["items"][0]["status"] == "failed"
    assert payload["items"][0]["error"] == "ValueError: boom"


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

    payload, status = qm.get_failed_jobs({})

    assert status == 200
    assert payload == {"items": [], "total_count": 0}
    assert removed == [("job-stale", False)]


def test_autopublish_product_schedules_presenter_then_publisher(monkeypatch):
    qm = _make_queue_manager()
    job_ids = iter(("presenter_task_product-1_101", "publisher_task_product-1_202"))
    presenter_job = object()
    publisher_job = object()
    calls: list[dict[str, Any]] = []

    monkeypatch.setattr(qm, "_build_unique_job_id", lambda _task_name, _worker_id: next(job_ids))

    def fake_enqueue_task(queue_name: str, task_name: str, *args, **kwargs):
        calls.append(
            {
                "queue_name": queue_name,
                "task_name": task_name,
                "args": args,
                "kwargs": kwargs,
            }
        )
        if task_name == "presenter_task":
            return presenter_job
        return publisher_job

    monkeypatch.setattr(qm, "enqueue_task", fake_enqueue_task)

    payload, status = qm.autopublish_product("product-1", "publisher-1")

    assert status == 200
    assert payload["presenter_job_id"] == "presenter_task_product-1_101"
    assert payload["publisher_job_id"] == "publisher_task_product-1_202"
    assert len(calls) == 2
    assert calls[0] == {
        "queue_name": "presenters",
        "task_name": "presenter_task",
        "args": ("product-1",),
        "kwargs": {
            "job_id": "presenter_task_product-1_101",
            "meta": {"task": "presenter_task", "user_id": None, "worker_id": "product-1", "worker_type": "presenter_task"},
        },
    }
    assert calls[1] == {
        "queue_name": "publishers",
        "task_name": "publisher_task",
        "args": ("product-1", "publisher-1"),
        "kwargs": {
            "job_id": "publisher_task_product-1_202",
            "depends_on": presenter_job,
            "meta": {"task": "publisher_task", "user_id": None, "worker_id": "publisher-1", "worker_type": "publisher_task"},
        },
    }


def test_enqueue_task_passes_meta_to_rq_queue(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue(self, task_func, *args, job_id=None, **kwargs):
            queue_calls.append({"task_func": task_func, "args": args, "job_id": job_id, "kwargs": kwargs})
            return True

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())

    result = qm.enqueue_task(
        "collectors",
        "collector_task",
        "source-1",
        True,
        job_id="collect_rss_collector_source-1",
        meta={"task": "collector_task", "user_id": None, "worker_id": "source-1", "worker_type": "rss_collector"},
    )

    assert result is True
    assert queue_calls == [
        {
            "task_func": "worker.collectors.collector_tasks.collector_task",
            "args": ("source-1", True),
            "job_id": "collect_rss_collector_source-1",
            "kwargs": {
                "at_front": False,
                "meta": {"task": "collector_task", "user_id": None, "worker_id": "source-1", "worker_type": "rss_collector"},
            },
        }
    ]


def test_enqueue_task_places_user_triggered_job_at_front(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue(self, task_func, *args, job_id=None, **kwargs):
            queue_calls.append({"task_func": task_func, "args": args, "job_id": job_id, "kwargs": kwargs})
            return object()

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())

    qm.enqueue_task(
        "presenters",
        "presenter_task",
        "product-1",
        job_id="presenter_task_product-1",
        meta={"task": "presenter_task", "user_id": "user-1", "worker_id": "product-1", "worker_type": "presenter_task"},
    )

    assert queue_calls[0]["kwargs"]["at_front"] is True


def test_user_triggered_jobs_run_lifo_ahead_of_background_jobs():
    queue = Queue("presenters", connection=fakeredis.FakeRedis())
    qm = _make_queue_manager()
    qm._queues = {"presenters": queue}

    qm.enqueue_task(
        "presenters",
        "presenter_task",
        "background-product",
        job_id="background-job",
        meta={"task": "presenter_task", "user_id": None, "worker_id": "background-product", "worker_type": "presenter_task"},
    )
    qm.enqueue_task(
        "presenters",
        "presenter_task",
        "first-user-product",
        job_id="first-user-job",
        meta={"task": "presenter_task", "user_id": "user-1", "worker_id": "first-user-product", "worker_type": "presenter_task"},
    )
    qm.enqueue_task(
        "presenters",
        "presenter_task",
        "second-user-product",
        job_id="second-user-job",
        meta={"task": "presenter_task", "user_id": "user-2", "worker_id": "second-user-product", "worker_type": "presenter_task"},
    )

    assert queue.job_ids == ["second-user-job", "first-user-job", "background-job"]


def test_enqueue_task_prioritizes_dependencies_for_user_triggered_job(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue(self, task_func, *args, job_id=None, **kwargs):
            queue_calls.append({"task_func": task_func, "args": args, "job_id": job_id, "kwargs": kwargs})
            return object()

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())

    qm.enqueue_task(
        "publishers",
        "publisher_task",
        "product-1",
        "publisher-1",
        depends_on=["presenter-job-1", "presenter-job-2"],
        meta={"task": "publisher_task", "user_id": "user-1", "worker_id": "publisher-1", "worker_type": "publisher_task"},
    )

    dependency = queue_calls[0]["kwargs"]["depends_on"]
    assert isinstance(dependency, qm_module.Dependency)
    assert dependency.dependencies == ["presenter-job-1", "presenter-job-2"]
    assert dependency.allow_failure is False
    assert dependency.enqueue_at_front is True


def test_enqueue_task_preserves_existing_dependency_options(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue(self, task_func, *args, job_id=None, **kwargs):
            queue_calls.append({"task_func": task_func, "args": args, "job_id": job_id, "kwargs": kwargs})
            return object()

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())
    existing_dependency = qm_module.Dependency("presenter-job", allow_failure=True)
    existing_dependency.custom_config = {"timeout": 120}

    qm.enqueue_task(
        "publishers",
        "publisher_task",
        "product-1",
        "publisher-1",
        depends_on=existing_dependency,
        meta={"task": "publisher_task", "user_id": "user-1", "worker_id": "publisher-1", "worker_type": "publisher_task"},
    )

    dependency = queue_calls[0]["kwargs"]["depends_on"]
    assert isinstance(dependency, qm_module.Dependency)
    assert dependency is not existing_dependency
    assert dependency.dependencies == ["presenter-job"]
    assert dependency.allow_failure is True
    assert dependency.enqueue_at_front is True
    assert dependency.custom_config == {"timeout": 120}
    assert existing_dependency.enqueue_at_front is False


def test_enqueue_at_preserves_user_priority(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue_at(self, scheduled_time, task_func, *args, job_id=None, **kwargs):
            queue_calls.append(
                {
                    "scheduled_time": scheduled_time,
                    "task_func": task_func,
                    "args": args,
                    "job_id": job_id,
                    "kwargs": kwargs,
                }
            )
            return object()

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())
    scheduled_time = datetime(2026, 7, 23, tzinfo=UTC)

    qm.enqueue_at(
        "presenters",
        "presenter_task",
        scheduled_time,
        "product-1",
        job_id="presenter_task_product-1",
        depends_on="collector-job",
        meta={"task": "presenter_task", "user_id": "user-1", "worker_id": "product-1", "worker_type": "presenter_task"},
    )

    assert queue_calls[0]["kwargs"]["at_front"] is True
    dependency = queue_calls[0]["kwargs"]["depends_on"]
    assert isinstance(dependency, qm_module.Dependency)
    assert dependency.dependencies == ["collector-job"]
    assert dependency.enqueue_at_front is True


def test_enqueue_at_keeps_background_job_at_normal_priority(monkeypatch):
    queue_calls = []

    class FakeQueue:
        def enqueue_at(self, scheduled_time, task_func, *args, job_id=None, **kwargs):
            queue_calls.append(
                {
                    "scheduled_time": scheduled_time,
                    "task_func": task_func,
                    "args": args,
                    "job_id": job_id,
                    "kwargs": kwargs,
                }
            )
            return object()

    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "get_queue", lambda _queue_name: FakeQueue())
    scheduled_time = datetime(2026, 7, 23, tzinfo=UTC)

    qm.enqueue_at(
        "presenters",
        "presenter_task",
        scheduled_time,
        "product-1",
        job_id="presenter_task_product-1",
        depends_on="collector-job",
        meta={"task": "presenter_task", "user_id": None, "worker_id": "product-1", "worker_type": "presenter_task"},
    )

    assert queue_calls[0]["kwargs"]["at_front"] is False
    assert queue_calls[0]["kwargs"]["depends_on"] == "collector-job"


def test_autopublish_product_returns_error_when_presenter_enqueue_fails(monkeypatch):
    qm = _make_queue_manager()
    monkeypatch.setattr(qm, "_build_unique_job_id", lambda _task_name, _worker_id: "presenter_task_product-2_303")
    monkeypatch.setattr(qm, "enqueue_task", lambda *args, **kwargs: False)

    payload, status = qm.autopublish_product("product-2", "publisher-2")

    assert status == 500
    assert payload == {"error": "Could not schedule presenter job for product"}


def test_osint_schedule_entries_include_metadata(monkeypatch):
    class FakeTask:
        def __init__(self):
            self.last_run = datetime(2025, 1, 1, 0, 0, 0)
            self.last_success = datetime(2025, 1, 1, 0, 0, 0)
            self.status = "FAILURE"
            self.result = '{"reason":"job_timeout"}'

    class FakeSource:
        def __init__(self):
            self.id = "source-1"
            self.name = "Source One"
            self.task_id = "task-1"
            self.cron_run_prefix = "cron_osint_source_source-1_"
            self.cron_job_id = "osint_source_source-1"

        def get_schedule(self):
            return "0 * * * *"

        def get_schedule_with_default(self):
            return self.get_schedule()

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [FakeSource()]))
    monkeypatch.setattr(
        TaskModel,
        "get_latest_matching",
        classmethod(lambda cls, exact_ids=None, prefixes=None, task_name=None: FakeTask()),
    )

    entries = OSINTSource.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries
    entry = entries[0]
    assert entry["id"] == "osint_source_source-1"
    assert entry["queue"] == "collectors"
    assert entry["last_reason"] == "job_timeout"
    assert entry["previous_run_time"]


def test_osint_schedule_entries_handle_many(monkeypatch):
    def make_source(idx: int):
        class FakeSource:
            def __init__(self, i):
                self.id = f"source-{i}"
                self.name = f"Source {i}"
                self.task_id = f"task-{i}"
                self.cron_run_prefix = f"cron_osint_source_source-{i}_"
                self.cron_job_id = f"osint_source_source-{i}"

            def get_schedule(self):
                return f"*/{(idx % 5) + 1} * * * *"

            def get_schedule_with_default(self):
                return self.get_schedule()

        return FakeSource(idx)

    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: [make_source(i) for i in range(120)]))
    monkeypatch.setattr(TaskModel, "get_latest_matching", classmethod(lambda cls, exact_ids=None, prefixes=None, task_name=None: None))

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


def test_bot_schedule_entries_include_last_reason(monkeypatch):
    class FakeTask:
        def __init__(self):
            self.last_run = datetime(2025, 1, 1, 0, 0, 0)
            self.last_success = datetime(2025, 1, 1, 0, 0, 0)
            self.status = "FAILURE"
            self.result = '{"reason":"job_failed"}'

    class FakeBot:
        def __init__(self):
            self.id = "bot-1"
            self.name = "Bot One"
            self.task_id = "task-1"
            self.cron_run_prefix = "cron_bot_bot-1_"
            self.cron_job_id = "bot_bot-1"

        def get_schedule(self):
            return "0 * * * *"

    monkeypatch.setattr(Bot, "get_all_for_collector", classmethod(lambda cls: [FakeBot()]))
    monkeypatch.setattr(
        TaskModel,
        "get_latest_matching",
        classmethod(lambda cls, exact_ids=None, prefixes=None, task_name=None: FakeTask()),
    )

    entries = Bot.get_enabled_schedule_entries(now=datetime(2025, 1, 1, 0, 0))

    assert entries
    assert entries[0]["last_reason"] == "job_failed"


def test_get_scheduled_jobs_with_many_sources(app, monkeypatch):
    def fake_osint_entries():
        return [
            {
                "id": f"osint_source_{i}",
                "name": f"Collector {i}",
                "queue": "collectors",
                "next_run_time": datetime(2025, 1, 1, 0, 0, 0) + timedelta(minutes=120 - i),
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

    with app.app_context():
        schedules, status = qm.get_scheduled_jobs({})

    assert status == 200
    # 120 OSINT cron jobs + two housekeeping crons
    assert schedules["total_count"] == 122
    assert len(schedules["items"]) == 20
    assert schedules["items"][0]["id"] == "osint_source_119"


def test_get_scheduled_jobs_filters_sorts_and_paginates(app, monkeypatch):
    def fake_osint_entries():
        return [
            {
                "id": f"osint_source_{index}",
                "name": name,
                "queue": "collectors",
                "next_run_time": datetime(2025, 1, 1, index, 0, 0),
                "schedule": "0 * * * *",
                "type": "cron",
            }
            for index, name in enumerate(["Alpha feed", "Beta feed", "Alpha archive"])
        ]

    monkeypatch.setattr(OSINTSource, "get_enabled_schedule_entries", classmethod(lambda cls: fake_osint_entries()))
    monkeypatch.setattr(Bot, "get_enabled_schedule_entries", classmethod(lambda cls: []))

    qm = _make_queue_manager()
    qm._redis = object()

    with app.app_context():
        schedules, status = qm.get_scheduled_jobs(
            {
                "search": "alpha",
                "order": "name_desc",
                "page": "2",
                "limit": "1",
            }
        )

    assert status == 200
    assert schedules["total_count"] == 2
    assert [job["name"] for job in schedules["items"]] == ["Alpha archive"]


def test_get_scheduled_jobs_uses_safe_paging_defaults(app, monkeypatch):
    monkeypatch.setattr(OSINTSource, "get_enabled_schedule_entries", classmethod(lambda cls: []))
    monkeypatch.setattr(Bot, "get_enabled_schedule_entries", classmethod(lambda cls: []))

    qm = _make_queue_manager()
    qm._redis = object()

    with app.app_context():
        schedules, status = qm.get_scheduled_jobs({"page": "invalid", "limit": "invalid"})

    assert status == 200
    assert schedules["total_count"] == 2
    assert {job["id"] for job in schedules["items"]} == {
        qm_module.TASK_HISTORY_CLEANUP_JOB_ID,
        qm_module.TOKEN_CLEANUP_JOB_ID,
    }


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
        "reconcile_task_failures": b'{"cron":"*/5 * * * *"}',
        "unconfigured_job": b'{"cron":"0 * * * *"}',
    }
    qm._redis.zsets["rq:cron:next"] = {  # type: ignore[attr-defined]
        "osint_source_stale": 1234.0,
        "bot_stale": 1234.0,
        "reconcile_task_failures": 1234.0,
        "unconfigured_job": 1234.0,
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
    assert "cleanup_token_blacklist" in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "cleanup_task_history" in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "osint_source_stale" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "bot_stale" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "reconcile_task_failures" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert "reconcile_task_failures" not in qm._redis.zsets["rq:cron:next"]  # type: ignore[index,attr-defined]
    assert "unconfigured_job" not in qm._redis.hashes["rq:cron:def"]  # type: ignore[index,attr-defined]
    assert len(purged_calls) == 1
    assert purged_calls[0][0] == set()
    assert set(purged_calls[0][1]) == {
        "cron_osint_source_stale_",
        "cron_bot_stale_",
        "cron_reconcile_task_failures_",
        "cron_unconfigured_job_",
    }
