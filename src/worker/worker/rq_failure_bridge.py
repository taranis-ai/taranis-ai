from __future__ import annotations

from typing import Any

from models.task_identity import get_meta_string, get_task_name_from_job
from rq.job import Job
from rq.timeouts import JobTimeoutException

from worker.core_api import CoreApi, build_failure_task_result
from worker.http_client import http_session_scope
from worker.log import logger
from worker.publishers.execution_context import PUBLISHER_DIAGNOSTICS_META_KEY, publisher_display_name


TERMINAL_TASK_STATUSES = {"SUCCESS", "WARNING", "FAILURE", "NOT_MODIFIED", "PREVIEW"}


@http_session_scope()
def rq_failure_exception_handler(job: Job, exc_type: type[BaseException], exc_value: BaseException, _traceback: Any) -> bool:
    if _has_terminal_task_result(job.id):
        return True

    reason = "job_timeout" if issubclass(exc_type, JobTimeoutException) else "job_failed"
    retryable = issubclass(exc_type, JobTimeoutException)
    meta = _refresh_meta(job)
    message, data = _safe_failure_details(meta, reason=reason, exception_type=exc_type.__name__)

    _persist_failure(
        job,
        message=message,
        reason=reason,
        retryable=retryable,
        data=data,
        meta=meta,
    )
    return True


@http_session_scope()
def rq_work_horse_killed_handler(job: Job, retpid: int, ret_val: int, _rusage: Any) -> None:
    if _has_terminal_task_result(job.id):
        return

    meta = _refresh_meta(job)
    message, data = _safe_failure_details(meta, reason="work_horse_killed")
    data |= {"retpid": retpid, "ret_val": ret_val}
    _persist_failure(
        job,
        message=message,
        reason="work_horse_killed",
        retryable=True,
        data=data,
        meta=meta,
    )


def _has_terminal_task_result(job_id: str) -> bool:
    try:
        payload = CoreApi().api_get(f"/tasks/{job_id}")
    except Exception as exc:
        logger.error(f"Failed to read task result before synthetic failure persistence for {job_id}: exception_type={type(exc).__name__}")
        return False

    status = payload.get("status") if isinstance(payload, dict) else None
    return isinstance(status, str) and status in TERMINAL_TASK_STATUSES


def _refresh_meta(job: Job) -> dict[str, Any]:
    try:
        refreshed = job.get_meta(refresh=True)
    except Exception as exc:
        logger.error(
            f"Failed to refresh task metadata before synthetic failure persistence for {job.id}: exception_type={type(exc).__name__}"
        )
        refreshed = job.meta if isinstance(job.meta, dict) else {}
    return refreshed if isinstance(refreshed, dict) else {}


def _persist_failure(
    job: Job, *, message: str, reason: str, retryable: bool, data: dict[str, Any], meta: dict[str, Any] | None = None
) -> None:
    meta = meta if isinstance(meta, dict) else _refresh_meta(job)
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


def _safe_failure_details(meta: dict[str, Any], *, reason: str, exception_type: str | None = None) -> tuple[str, dict[str, Any]]:
    diagnostics = meta.get(PUBLISHER_DIAGNOSTICS_META_KEY) if isinstance(meta, dict) else None
    data: dict[str, Any] = {}
    if exception_type:
        data["exception_type"] = exception_type
    if not isinstance(diagnostics, dict):
        message = "Background job exceeded its execution timeout" if reason == "job_timeout" else "Background job failed"
        if reason == "work_horse_killed":
            message = "Worker process ended before the job completed"
        return message, data

    for source_key, result_key in (
        ("product_id", "product_id"),
        ("publisher_id", "publisher_id"),
        ("publisher_type", "publisher_type"),
        ("phase", "publisher_phase"),
    ):
        value = diagnostics.get(source_key)
        if isinstance(value, str) and value.strip():
            data[result_key] = value.strip()

    publisher_name = publisher_display_name(data.get("publisher_type"))
    phase = data.get("publisher_phase")
    if reason == "job_timeout" and phase:
        return f"{publisher_name} publisher timed out during {phase}", data
    if reason == "work_horse_killed" and phase:
        return f"{publisher_name} publisher stopped during {phase}", data
    return "Publisher task failed", data
