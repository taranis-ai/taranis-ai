from __future__ import annotations

from typing import Any

from models.task_identity import get_meta_string, get_task_name_from_job
from rq.job import Job
from rq.timeouts import JobTimeoutException

from worker.core_api import CoreApi, build_failure_task_result
from worker.log import logger


TERMINAL_TASK_STATUSES = {"SUCCESS", "FAILURE", "NOT_MODIFIED", "PREVIEW"}


def rq_failure_exception_handler(job: Job, exc_type: type[BaseException], exc_value: BaseException, _traceback: Any) -> bool:
    if _has_terminal_task_result(job.id):
        return True

    reason = "job_timeout" if issubclass(exc_type, JobTimeoutException) else "job_failed"
    retryable = issubclass(exc_type, JobTimeoutException)
    message = str(exc_value) or exc_type.__name__

    _persist_failure(
        job,
        message=message,
        reason=reason,
        retryable=retryable,
        data={"exception_type": exc_type.__name__, "message": message},
    )
    return True


def rq_work_horse_killed_handler(job: Job, retpid: int, ret_val: int, _rusage: Any) -> None:
    if _has_terminal_task_result(job.id):
        return

    _persist_failure(
        job,
        message=f"Work horse killed for job {job.id}",
        reason="work_horse_killed",
        retryable=True,
        data={"retpid": retpid, "ret_val": ret_val},
    )


def _has_terminal_task_result(job_id: str) -> bool:
    try:
        payload = CoreApi().api_get(f"/tasks/{job_id}")
    except Exception:
        logger.exception(f"Failed to read task result before synthetic failure persistence for {job_id}")
        return False

    status = payload.get("status") if isinstance(payload, dict) else None
    return isinstance(status, str) and status in TERMINAL_TASK_STATUSES


def _persist_failure(job: Job, *, message: str, reason: str, retryable: bool, data: dict[str, Any]) -> None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    task_name = get_task_name_from_job(job, meta)
    worker_id = get_meta_string(meta, "worker_id")
    worker_type = get_meta_string(meta, "worker_type")
    user_id = get_meta_string(meta, "user_id")

    if not task_name:
        logger.warning(f"Skipping synthetic failure persistence for {job.id} because task identity is missing")
        return

    CoreApi().save_task_result(
        job.id,
        task_name,
        "FAILURE",
        user_id=user_id,
        worker_id=worker_id,
        worker_type=worker_type,
        result=build_failure_task_result(message, reason=reason, retryable=retryable, data=data),
    )
