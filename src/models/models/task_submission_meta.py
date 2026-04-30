from typing import Any, TypeAlias, TypedDict, TypeGuard


class TaskSubmissionMeta(TypedDict):
    task: str
    worker_id: str
    worker_type: str


WorkerTaskPayload: TypeAlias = dict[str, Any]


def build_worker_task_payload(
    task: str,
    worker_id: str,
    worker_type: str | None = None,
    fields: dict[str, Any] | None = None,
) -> WorkerTaskPayload:
    payload: WorkerTaskPayload = {
        "task": task,
        "worker_id": worker_id,
        "worker_type": worker_type or task,
    }
    if fields:
        payload.update(fields)
    return payload


def _has_task_submission_fields(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return isinstance(value.get("task"), str) and isinstance(value.get("worker_id"), str) and isinstance(value.get("worker_type"), str)


def is_task_submission_meta(value: Any) -> TypeGuard[TaskSubmissionMeta]:
    return _has_task_submission_fields(value)


def is_worker_task_payload(value: Any) -> TypeGuard[WorkerTaskPayload]:
    return _has_task_submission_fields(value)


def build_task_submission_meta(payload: WorkerTaskPayload) -> TaskSubmissionMeta:
    return {
        "task": payload["task"],
        "worker_id": payload["worker_id"],
        "worker_type": payload["worker_type"],
    }
