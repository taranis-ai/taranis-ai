import json
from datetime import datetime, timedelta, timezone
from typing import Any

import rq.registry as rq_registry
from models.task import TaskResultEnvelope, TaskSubmission
from redis import Redis
from rq.job import Job

from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.managers.queue_manager import CRON_DEFS_KEY, CRON_NEXT_KEY
from core.model.task import Task as TaskModel
from core.service.task import TaskService


FAILURE_REASONS = (
    "cron_missed",
    "job_stalled_in_scheduled",
    "job_stalled_in_queue",
    "job_abandoned_after_start",
)


class TaskReconciliationService:
    def __init__(self):
        self._grace = timedelta(seconds=Config.RQ_RECONCILE_GRACE_SECONDS)
        self._started_grace = timedelta(seconds=Config.RQ_RECONCILE_STARTED_GRACE_SECONDS)

    def reconcile(self, now: datetime | None = None) -> dict[str, Any]:
        raw_now = now or datetime.now(timezone.utc)
        current_now = (
            raw_now if raw_now.tzinfo is None or raw_now.utcoffset() is None else raw_now.astimezone(timezone.utc).replace(tzinfo=None)
        )
        qm = getattr(queue_manager, "queue_manager", None)
        redis_conn = getattr(qm, "redis", None) if qm else None
        queues = getattr(qm, "_queues", {}) if qm else {}
        if redis_conn is None or not queues:
            return {
                "reconciled": 0,
                "details": {reason: 0 for reason in FAILURE_REASONS},
                "message": "Task reconciliation skipped because queue manager is not ready",
            }

        details = {
            "cron_missed": self._reconcile_cron_missed(redis_conn, queues, current_now),
            "job_stalled_in_scheduled": self._reconcile_scheduled(redis_conn, queues, current_now),
            "job_stalled_in_queue": self._reconcile_queued(redis_conn, queues, current_now),
            "job_abandoned_after_start": self._reconcile_started(redis_conn, queues, current_now),
        }
        return {
            "reconciled": sum(details.values()),
            "details": details,
            "message": "Task reconciliation completed",
        }

    def _reconcile_cron_missed(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        persisted = 0
        live_ids = set()
        for registry_cls in (rq_registry.ScheduledJobRegistry, rq_registry.StartedJobRegistry, rq_registry.FailedJobRegistry):
            live_ids |= self._registry_ids(queues, registry_cls)
        for queue in queues.values():
            try:
                live_ids |= set(queue.get_job_ids())
            except Exception:
                logger.exception("Failed collecting ready queue ids during reconciliation")

        try:
            raw_specs = redis_conn.hgetall(CRON_DEFS_KEY)
        except Exception:
            logger.exception("Failed reading cron definitions during task reconciliation")
            return 0

        for raw_job_id, raw_spec in raw_specs.items():
            try:
                spec = json.loads(raw_spec.decode() if isinstance(raw_spec, bytes) else str(raw_spec))
            except Exception:
                logger.exception("Ignoring invalid cron scheduler spec during reconciliation")
                continue

            if not isinstance(spec, dict) or not spec.get("cron"):
                continue

            job_id = raw_job_id.decode() if isinstance(raw_job_id, bytes) else str(raw_job_id)
            due_ts = redis_conn.zscore(CRON_NEXT_KEY, job_id)
            if due_ts is None:
                continue

            try:
                due_at = datetime.fromtimestamp(float(due_ts), tz=timezone.utc).replace(tzinfo=None)
                missed_job_id = f"cron_{job_id}_{int(due_ts)}"
                if due_at + self._grace > now or missed_job_id in live_ids or self._has_terminal_result(missed_job_id):
                    continue

                persisted += int(
                    self._persist_failure(
                        job_id=missed_job_id,
                        task_name=(
                            str(meta.get("task")).strip()
                            if isinstance((meta := spec.get("meta")), dict) and meta.get("task") is not None
                            else None
                        )
                        or str(spec.get("func_path") or ""),
                        meta=meta,
                        message=f"Cron slot for {job_id} was missed",
                        reason="cron_missed",
                        data={"cron_job_id": job_id, "due_at": due_at.isoformat(), "queue_name": spec.get("queue_name")},
                    )
                )
            except Exception:
                logger.exception(f"Failed reconciling missed cron job {job_id}")

        return persisted

    def _reconcile_scheduled(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        persisted = 0
        for queue_name, queue in queues.items():
            try:
                registry = rq_registry.ScheduledJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
            except Exception:
                logger.exception("Failed reading ScheduledJobRegistry for %s", queue_name)
                continue

            for job_id in job_ids:
                try:
                    if self._has_terminal_result(job_id):
                        continue

                    scheduled_for = self._utc_naive(registry.get_scheduled_time(job_id))
                    if scheduled_for is None or scheduled_for + self._grace > now:
                        continue
                    job = Job.fetch(job_id, connection=redis_conn)
                    meta = job.meta if isinstance(job.meta, dict) else {}
                    task_name = self._resolve_task_name_from_job(job)
                    if not task_name:
                        continue

                    persisted += int(
                        self._persist_failure(
                            job_id=job_id,
                            task_name=task_name,
                            meta=meta,
                            message=f"Scheduled job {job_id} remained delayed past its release time",
                            reason="job_stalled_in_scheduled",
                            data={"queue_name": queue_name, "scheduled_for": scheduled_for.isoformat()},
                        )
                    )
                except Exception:
                    logger.exception(f"Failed reconciling scheduled job {job_id}")
                    continue

        return persisted

    def _reconcile_queued(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        persisted = 0
        blocked_ids = self._registry_ids(queues, rq_registry.ScheduledJobRegistry)
        blocked_ids |= self._registry_ids(queues, rq_registry.StartedJobRegistry)
        blocked_ids |= self._registry_ids(queues, rq_registry.FailedJobRegistry)

        for queue_name, queue in queues.items():
            try:
                job_ids = list(queue.get_job_ids())
            except Exception:
                logger.exception("Failed reading ready queue %s", queue_name)
                continue

            for job_id in job_ids:
                try:
                    if job_id in blocked_ids or self._has_terminal_result(job_id):
                        continue

                    job = Job.fetch(job_id, connection=redis_conn)
                    meta = job.meta if isinstance(job.meta, dict) else {}
                    task_name = self._resolve_task_name_from_job(job)
                    if not task_name:
                        continue

                    enqueued_at = self._utc_naive(getattr(job, "enqueued_at", None) or getattr(job, "created_at", None))
                    if enqueued_at is None or enqueued_at + self._grace > now:
                        continue

                    persisted += int(
                        self._persist_failure(
                            job_id=job_id,
                            task_name=task_name,
                            meta=meta,
                            message=f"Queued job {job_id} waited too long without being claimed",
                            reason="job_stalled_in_queue",
                            data={"queue_name": queue_name, "enqueued_at": enqueued_at.isoformat()},
                        )
                    )
                except Exception:
                    logger.exception(f"Failed reconciling queued job {job_id}")
                    continue

        return persisted

    def _reconcile_started(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        persisted = 0
        failed_ids = self._registry_ids(queues, rq_registry.FailedJobRegistry)

        for queue_name, queue in queues.items():
            try:
                registry = rq_registry.StartedJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
            except Exception:
                logger.exception("Failed reading StartedJobRegistry for %s", queue_name)
                continue

            for job_id in job_ids:
                try:
                    if job_id in failed_ids or self._has_terminal_result(job_id):
                        continue

                    job = Job.fetch(job_id, connection=redis_conn)
                    meta = job.meta if isinstance(job.meta, dict) else {}
                    task_name = self._resolve_task_name_from_job(job)
                    if not task_name:
                        continue

                    started_at = self._utc_naive(getattr(job, "started_at", None))
                    if started_at is None or started_at + self._started_grace > now:
                        continue

                    persisted += int(
                        self._persist_failure(
                            job_id=job_id,
                            task_name=task_name,
                            meta=meta,
                            message=f"Started job {job_id} disappeared without a terminal task result",
                            reason="job_abandoned_after_start",
                            data={"queue_name": queue_name, "started_at": started_at.isoformat()},
                        )
                    )
                except Exception:
                    logger.exception(f"Failed reconciling started job {job_id}")
                    continue

        return persisted

    def _persist_failure(
        self,
        *,
        job_id: str,
        task_name: str,
        meta: dict[str, Any] | None,
        message: str,
        reason: str,
        data: dict[str, Any],
    ) -> bool:
        meta = meta if isinstance(meta, dict) else None
        existing = TaskModel.get_by_job_id(job_id)
        existing_reason = (existing.to_dict().get("result") or {}).get("reason") if existing and existing.result else None
        if existing and existing.status == "FAILURE" and existing_reason == reason:
            return False

        user_id = str(meta.get("user_id")).strip() if meta and meta.get("user_id") is not None and str(meta.get("user_id")).strip() else None
        worker_id = (
            str(meta.get("worker_id")).strip() if meta and meta.get("worker_id") is not None and str(meta.get("worker_id")).strip() else None
        )
        worker_type = (
            str(meta.get("worker_type")).strip()
            if meta and meta.get("worker_type") is not None and str(meta.get("worker_type")).strip()
            else None
        )

        TaskService.save_task_result(
            TaskSubmission(
                id=job_id,
                task=task_name,
                user_id=user_id,
                worker_id=worker_id,
                worker_type=worker_type,
                status="FAILURE",
                result=TaskResultEnvelope(message=message, reason=reason, retryable=True, data=data),
            )
        )
        return True

    @staticmethod
    def _resolve_task_name_from_job(job: Job) -> str | None:
        meta = job.meta if isinstance(job.meta, dict) else {}
        task_name = str(meta.get("task")).strip() if meta.get("task") is not None and str(meta.get("task")).strip() else None
        if task_name:
            return task_name

        short_name = (getattr(job, "func_name", "") or "").rsplit(".", 1)[-1]
        if not short_name:
            return None
        return "collector_task" if short_name == "fetch_single_news_item" else short_name

    @staticmethod
    def _registry_ids(queues: dict[str, Any], registry_cls: Any) -> set[str]:
        job_ids: set[str] = set()
        for queue in queues.values():
            try:
                job_ids |= set(registry_cls(queue=queue).get_job_ids())
            except Exception:
                logger.exception("Failed reading %s during reconciliation", getattr(registry_cls, "__name__", registry_cls))
        return job_ids

    @staticmethod
    def _has_terminal_result(job_id: str) -> bool:
        task = TaskModel.get_by_job_id(job_id)
        return bool(task and task.status in (TaskModel.SUCCESS_STATUSES | TaskModel.FAILURE_STATUSES))

    @staticmethod
    def _utc_naive(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


task_reconciliation_service = TaskReconciliationService()
