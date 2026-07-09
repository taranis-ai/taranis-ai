import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import rq.registry as rq_registry
from models.task import TaskResultEnvelope, TaskSubmission
from models.task_identity import get_meta_string, get_task_name_from_job, get_task_name_from_spec
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

JobTimestampGetter = Callable[[str, Job], datetime | None]


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

            cron_job_id = raw_job_id.decode() if isinstance(raw_job_id, bytes) else str(raw_job_id)
            due_ts = redis_conn.zscore(CRON_NEXT_KEY, cron_job_id)
            if due_ts is None:
                continue

            try:
                due_at = datetime.fromtimestamp(float(due_ts), tz=timezone.utc).replace(tzinfo=None)
            except (TypeError, ValueError, OSError):
                logger.exception("Ignoring invalid cron due timestamp during reconciliation for %s", cron_job_id)
                continue

            missed_job_id = f"cron_{cron_job_id}_{int(due_ts)}"
            if due_at + self._grace > now or missed_job_id in live_ids or self._has_terminal_result(missed_job_id):
                continue

            try:
                meta = spec.get("meta") if isinstance(spec.get("meta"), dict) else None
                task_name = get_task_name_from_spec(spec)
                if not task_name:
                    continue

                persisted += int(
                    self._persist_failure(
                        job_id=missed_job_id,
                        task_name=task_name,
                        meta=meta,
                        message=f"Cron slot for {cron_job_id} was missed",
                        reason="cron_missed",
                        data={"cron_job_id": cron_job_id, "due_at": due_at.isoformat(), "queue_name": spec.get("queue_name")},
                    )
                )
            except Exception:
                logger.exception(f"Failed reconciling missed cron job {cron_job_id}")

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

            persisted += self._reconcile_jobs(
                redis_conn=redis_conn,
                queue_name=queue_name,
                job_ids=job_ids,
                now=now,
                threshold=self._grace,
                reason="job_stalled_in_scheduled",
                get_timestamp=lambda job_id, _job: registry.get_scheduled_time(job_id),
                message_template="Scheduled job {job_id} remained delayed past its release time",
                data_timestamp_key="scheduled_for",
            )

        return persisted

    def _reconcile_queued(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        blocked_ids = self._registry_ids(queues, rq_registry.ScheduledJobRegistry)
        blocked_ids |= self._registry_ids(queues, rq_registry.StartedJobRegistry)
        blocked_ids |= self._registry_ids(queues, rq_registry.FailedJobRegistry)

        persisted = 0
        for queue_name, queue in queues.items():
            try:
                job_ids = list(queue.get_job_ids())
            except Exception:
                logger.exception("Failed reading ready queue %s", queue_name)
                continue

            persisted += self._reconcile_jobs(
                redis_conn=redis_conn,
                queue_name=queue_name,
                job_ids=job_ids,
                skip_ids=blocked_ids,
                now=now,
                threshold=self._grace,
                reason="job_stalled_in_queue",
                get_timestamp=lambda _job_id, job: getattr(job, "enqueued_at", None) or getattr(job, "created_at", None),
                message_template="Queued job {job_id} waited too long without being claimed",
                data_timestamp_key="enqueued_at",
            )

        return persisted

    def _reconcile_started(self, redis_conn: Redis, queues: dict[str, Any], now: datetime) -> int:
        failed_ids = self._registry_ids(queues, rq_registry.FailedJobRegistry)

        persisted = 0
        for queue_name, queue in queues.items():
            try:
                registry = rq_registry.StartedJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
            except Exception:
                logger.exception("Failed reading StartedJobRegistry for %s", queue_name)
                continue

            persisted += self._reconcile_jobs(
                redis_conn=redis_conn,
                queue_name=queue_name,
                job_ids=job_ids,
                skip_ids=failed_ids,
                now=now,
                threshold=self._started_grace,
                reason="job_abandoned_after_start",
                get_timestamp=lambda _job_id, job: getattr(job, "started_at", None),
                message_template="Started job {job_id} disappeared without a terminal task result",
                data_timestamp_key="started_at",
            )

        return persisted

    def _reconcile_jobs(
        self,
        *,
        redis_conn: Redis,
        queue_name: str,
        job_ids: list[str],
        now: datetime,
        threshold: timedelta,
        reason: str,
        get_timestamp: JobTimestampGetter,
        message_template: str,
        data_timestamp_key: str,
        skip_ids: set[str] | None = None,
    ) -> int:
        persisted = 0
        skipped_ids = skip_ids or set()

        for job_id in job_ids:
            try:
                if job_id in skipped_ids or self._has_terminal_result(job_id):
                    continue

                job = Job.fetch(job_id, connection=redis_conn)
                meta = job.meta if isinstance(job.meta, dict) else None
                task_name = get_task_name_from_job(job, meta)
                if not task_name:
                    continue

                timestamp = self._utc_naive(get_timestamp(job_id, job))
                if timestamp is None:
                    continue

                if timestamp + threshold > now:
                    continue

                persisted += int(
                    self._persist_failure(
                        job_id=job_id,
                        task_name=task_name,
                        meta=meta,
                        message=message_template.format(job_id=job_id),
                        reason=reason,
                        data={"queue_name": queue_name, data_timestamp_key: timestamp.isoformat()},
                    )
                )
            except Exception:
                logger.exception("Failed reconciling %s for %s", reason, job_id)

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

        user_id = get_meta_string(meta, "user_id")
        worker_id = get_meta_string(meta, "worker_id")
        worker_type = get_meta_string(meta, "worker_type")

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
