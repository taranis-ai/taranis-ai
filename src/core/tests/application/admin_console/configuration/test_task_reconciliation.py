import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from core.managers import queue_manager
from core.managers.queue_manager import _annotate_jobs
from core.model.task import Task as TaskModel
from core.service import task_reconciliation
from core.service.task_reconciliation import task_reconciliation_service


pytestmark = pytest.mark.usefixtures("_clean_registries")


class FakeRedis:
    def __init__(self, *, cron_defs: dict[str, Any] | None = None, cron_next: dict[str, float] | None = None):
        self.cron_defs = {}
        for job_id, spec in (cron_defs or {}).items():
            if isinstance(spec, bytes):
                self.cron_defs[job_id] = spec
            elif isinstance(spec, str):
                self.cron_defs[job_id] = spec.encode()
            else:
                self.cron_defs[job_id] = json.dumps(spec).encode()
        self.cron_next = dict(cron_next or {})

    def hgetall(self, key: str):
        if key == "rq:cron:def":
            return self.cron_defs
        return {}

    def zscore(self, key: str, member: str):
        if key == "rq:cron:next":
            return self.cron_next.get(member)
        return None


class FakeQueue:
    def __init__(self, name: str, job_ids: list[str] | None = None):
        self.name = name
        self._job_ids = list(job_ids or [])

    def get_job_ids(self):
        return list(self._job_ids)


class FakeJob:
    def __init__(
        self,
        job_id: str,
        *,
        meta: dict[str, Any] | None = None,
        func_name: str = "worker.collectors.collector_tasks.collector_task",
        enqueued_at: datetime | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
    ):
        self.id = job_id
        self.meta = dict(meta or {})
        self.func_name = func_name
        self.enqueued_at = enqueued_at
        self.created_at = created_at
        self.started_at = started_at


class FakeScheduledRegistry:
    jobs_by_queue: dict[str, list[str]] = {}
    times_by_job_id: dict[str, datetime] = {}

    def __init__(self, queue):
        self.queue = queue

    def get_job_ids(self):
        return list(self.jobs_by_queue.get(self.queue.name, []))

    def get_scheduled_time(self, job_id: str):
        return self.times_by_job_id[job_id]


class FakeStartedRegistry:
    jobs_by_queue: dict[str, list[str]] = {}

    def __init__(self, queue):
        self.queue = queue

    def get_job_ids(self):
        return list(self.jobs_by_queue.get(self.queue.name, []))


class FakeFailedRegistry:
    jobs_by_queue: dict[str, list[str]] = {}

    def __init__(self, queue):
        self.queue = queue

    def get_job_ids(self):
        return list(self.jobs_by_queue.get(self.queue.name, []))


def _install_fake_queue_manager(monkeypatch, *, redis_conn: FakeRedis, queues: dict[str, FakeQueue]) -> None:
    fake_qm = type("FakeQueueManager", (), {"redis": redis_conn, "_queues": queues})()
    monkeypatch.setattr(task_reconciliation.queue_manager, "queue_manager", fake_qm)


def _install_fake_registries(monkeypatch) -> None:
    monkeypatch.setattr(task_reconciliation.rq_registry, "ScheduledJobRegistry", FakeScheduledRegistry)
    monkeypatch.setattr(task_reconciliation.rq_registry, "StartedJobRegistry", FakeStartedRegistry)
    monkeypatch.setattr(task_reconciliation.rq_registry, "FailedJobRegistry", FakeFailedRegistry)


def _install_fake_job_fetch(monkeypatch, jobs: dict[str, FakeJob]) -> None:
    monkeypatch.setattr(task_reconciliation.Job, "fetch", staticmethod(lambda job_id, connection=None: jobs[job_id]))


# pyright: ignore[reportUnusedFunction] - pytest resolves this fixture via module-level pytestmark.usefixtures(...)
@pytest.fixture
def _clean_registries():
    FakeScheduledRegistry.jobs_by_queue = {}
    FakeScheduledRegistry.times_by_job_id = {}
    FakeStartedRegistry.jobs_by_queue = {}
    FakeFailedRegistry.jobs_by_queue = {}
    yield


def test_reconcile_cron_missed_persists_failure_and_is_idempotent(app, monkeypatch):
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    due_at = now - timedelta(minutes=10)
    cron_job_id = f"osint_source_{uuid.uuid4().hex}"
    missed_job_id = f"cron_{cron_job_id}_{int(due_at.timestamp())}"
    redis_conn = FakeRedis(
        cron_defs={
            cron_job_id: {
                "queue_name": "collectors",
                "func_path": "collector_task",
                "cron": "*/5 * * * *",
                "meta": {"task": "collector_task", "worker_id": "source-1", "worker_type": "rss_collector"},
            }
        },
        cron_next={cron_job_id: due_at.timestamp()},
    )
    _install_fake_queue_manager(monkeypatch, redis_conn=redis_conn, queues={"collectors": FakeQueue("collectors")})
    _install_fake_registries(monkeypatch)
    _install_fake_job_fetch(monkeypatch, {})

    with app.app_context():
        try:
            first = task_reconciliation_service.reconcile(now)
            second = task_reconciliation_service.reconcile(now)
            task = TaskModel.get(missed_job_id)

            assert first["details"]["cron_missed"] == 1
            assert second["details"]["cron_missed"] == 0
            assert task is not None
            assert task.status == "FAILURE"
            assert task.to_dict()["result"]["reason"] == "cron_missed"
        finally:
            if TaskModel.get(missed_job_id):
                TaskModel.delete(missed_job_id)


def test_reconcile_skips_cron_slot_when_real_run_exists(app, monkeypatch):
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    due_at = now - timedelta(minutes=10)
    cron_job_id = f"osint_source_{uuid.uuid4().hex}"
    missed_job_id = f"cron_{cron_job_id}_{int(due_at.timestamp())}"
    redis_conn = FakeRedis(
        cron_defs={
            cron_job_id: {
                "queue_name": "collectors",
                "func_path": "collector_task",
                "cron": "*/5 * * * *",
                "meta": {"task": "collector_task", "worker_id": "source-1", "worker_type": "rss_collector"},
            }
        },
        cron_next={cron_job_id: due_at.timestamp()},
    )
    _install_fake_queue_manager(monkeypatch, redis_conn=redis_conn, queues={"collectors": FakeQueue("collectors")})
    _install_fake_registries(monkeypatch)
    _install_fake_job_fetch(monkeypatch, {})

    with app.app_context():
        try:
            TaskModel.add(
                {
                    "id": missed_job_id,
                    "task": "collector_task",
                    "worker_id": "source-1",
                    "worker_type": "rss_collector",
                    "status": "SUCCESS",
                    "result": {"message": "ok", "reason": None, "retryable": False, "data": None},
                }
            )

            result = task_reconciliation_service.reconcile(now)

            assert result["details"]["cron_missed"] == 0
        finally:
            if TaskModel.get(missed_job_id):
                TaskModel.delete(missed_job_id)


def test_reconcile_cron_specs_ignore_invalid_entries_and_use_func_path_fallback(app, monkeypatch):
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    due_at = now - timedelta(minutes=10)
    cron_job_id = f"osint_source_{uuid.uuid4().hex}"
    missed_job_id = f"cron_{cron_job_id}_{int(due_at.timestamp())}"
    redis_conn = FakeRedis(
        cron_defs={
            "broken-json": b"{not-json",
            "not-a-dict": "[]",
            "not-cron": {"queue_name": "collectors", "func_path": "worker.collectors.collector_tasks.collector_task"},
            cron_job_id: {
                "queue_name": "collectors",
                "func_path": "worker.collectors.collector_tasks.fetch_single_news_item",
                "cron": "*/5 * * * *",
                "meta": {"task": "   ", "worker_id": " source-1 ", "worker_type": "   ", "user_id": " user-1 "},
            },
        },
        cron_next={cron_job_id: due_at.timestamp()},
    )
    _install_fake_queue_manager(monkeypatch, redis_conn=redis_conn, queues={"collectors": FakeQueue("collectors")})
    _install_fake_registries(monkeypatch)
    _install_fake_job_fetch(monkeypatch, {})

    with app.app_context():
        try:
            result = task_reconciliation_service.reconcile(now)
            task = TaskModel.get(missed_job_id)

            assert result["details"]["cron_missed"] == 1
            assert task is not None
            assert task.task == "collector_task"
            assert task.user_id == "user-1"
            assert task.worker_id == "source-1"
            assert task.worker_type is None
        finally:
            if TaskModel.get(missed_job_id):
                TaskModel.delete(missed_job_id)


def test_reconcile_scheduled_queue_and_started_failures_show_up_in_tasks_api(client, api_header, app, monkeypatch):
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    scheduled_job_id = f"presenter_task_{uuid.uuid4().hex}"
    queued_job_id = f"bot_{uuid.uuid4().hex}"
    started_job_id = f"publisher_task_{uuid.uuid4().hex}"
    jobs = {
        scheduled_job_id: FakeJob(
            scheduled_job_id,
            meta={"task": "presenter_task", "worker_id": "product-1", "worker_type": "presenter_task"},
            func_name="worker.presenters.presenter_tasks.presenter_task",
        ),
        queued_job_id: FakeJob(
            queued_job_id,
            meta={"task": queued_job_id, "worker_id": "bot-1", "worker_type": "WORDLIST_BOT"},
            func_name="worker.bots.bot_tasks.bot_task",
            enqueued_at=now - timedelta(minutes=10),
        ),
        started_job_id: FakeJob(
            started_job_id,
            meta={"task": "publisher_task", "worker_id": "publisher-1", "worker_type": "publisher_task"},
            func_name="worker.publishers.publisher_tasks.publisher_task",
            started_at=now - timedelta(minutes=10),
        ),
    }
    queues = {
        "presenters": FakeQueue("presenters"),
        "bots": FakeQueue("bots", [queued_job_id]),
        "publishers": FakeQueue("publishers"),
    }
    redis_conn = FakeRedis()

    FakeScheduledRegistry.jobs_by_queue = {"presenters": [scheduled_job_id]}
    FakeScheduledRegistry.times_by_job_id = {scheduled_job_id: now - timedelta(minutes=10)}
    FakeStartedRegistry.jobs_by_queue = {"publishers": [started_job_id]}

    _install_fake_queue_manager(monkeypatch, redis_conn=redis_conn, queues=queues)
    _install_fake_registries(monkeypatch)
    _install_fake_job_fetch(monkeypatch, jobs)

    with app.app_context():
        try:
            result = task_reconciliation_service.reconcile(now)
            scheduled_response = client.get(f"/api/tasks/{scheduled_job_id}", headers=api_header)
            queued_response = client.get(f"/api/tasks/{queued_job_id}", headers=api_header)
            started_response = client.get(f"/api/tasks/{started_job_id}", headers=api_header)

            assert result["details"] == {
                "cron_missed": 0,
                "job_stalled_in_scheduled": 1,
                "job_stalled_in_queue": 1,
                "job_abandoned_after_start": 1,
            }
            assert scheduled_response.status_code == 200
            assert queued_response.status_code == 200
            assert started_response.status_code == 200
            assert scheduled_response.get_json()["result"]["reason"] == "job_stalled_in_scheduled"
            assert queued_response.get_json()["result"]["reason"] == "job_stalled_in_queue"
            assert started_response.get_json()["result"]["reason"] == "job_abandoned_after_start"
            assert TaskModel.get_admin_menu_badges()["bot"] >= 1
        finally:
            for task_id in (scheduled_job_id, queued_job_id, started_job_id):
                if TaskModel.get(task_id):
                    TaskModel.delete(task_id)


@pytest.mark.parametrize(
    ("meta", "func_name", "expected_task", "expected_user_id", "expected_worker_id"),
    [
        (
            {"task": " presenter_task ", "user_id": " user-1 ", "worker_id": " product-1 ", "worker_type": " presenter_task "},
            "worker.presenters.presenter_tasks.presenter_task",
            "presenter_task",
            "user-1",
            "product-1",
        ),
        (
            {"task": "   ", "user_id": "   ", "worker_id": "source-2", "worker_type": "rss_collector"},
            "worker.presenters.presenter_tasks.presenter_task",
            "presenter_task",
            None,
            "source-2",
        ),
        (
            {"worker_id": "source-3", "worker_type": "rss_collector"},
            "worker.collectors.collector_tasks.fetch_single_news_item",
            "collector_task",
            None,
            "source-3",
        ),
    ],
)
def test_reconcile_queued_normalizes_task_identity_and_meta(
    app, monkeypatch, meta, func_name, expected_task, expected_user_id, expected_worker_id
):
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    job_id = f"queued_{uuid.uuid4().hex}"
    jobs = {
        job_id: FakeJob(
            job_id,
            meta=meta,
            func_name=func_name,
            enqueued_at=now - timedelta(minutes=10),
        )
    }
    _install_fake_queue_manager(monkeypatch, redis_conn=FakeRedis(), queues={"collectors": FakeQueue("collectors", [job_id])})
    _install_fake_registries(monkeypatch)
    _install_fake_job_fetch(monkeypatch, jobs)

    with app.app_context():
        try:
            result = task_reconciliation_service.reconcile(now)
            task = TaskModel.get(job_id)

            assert result["details"]["job_stalled_in_queue"] == 1
            assert task is not None
            assert task.task == expected_task
            assert task.user_id == expected_user_id
            assert task.worker_id == expected_worker_id
        finally:
            if TaskModel.get(job_id):
                TaskModel.delete(job_id)


def test_annotate_jobs_uses_reason_labels_from_persisted_failures(monkeypatch):
    fixed_now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(queue_manager, "datetime", _FixedDateTime)

    annotated = _annotate_jobs(
        [
            {
                "id": "scheduled-job",
                "type": "scheduled",
                "next_run_time": fixed_now - timedelta(minutes=30),
                "last_run": fixed_now - timedelta(minutes=30),
                "last_status": "FAILURE",
                "last_reason": "job_stalled_in_scheduled",
            },
            {
                "id": "cron-job",
                "type": "cron",
                "schedule": "*/5 * * * *",
                "previous_run_time": fixed_now - timedelta(minutes=5),
                "next_run_time": fixed_now + timedelta(minutes=5),
                "last_run": fixed_now - timedelta(minutes=5),
                "last_status": "FAILURE",
                "last_reason": "cron_missed",
            },
        ]
    )

    assert annotated[0]["status_badge"]["label"] == "Stalled"
    assert annotated[1]["status_badge"]["label"] == "Missed"
