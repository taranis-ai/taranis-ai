from typing import Any, TypedDict, TypeGuard


class TaskSubmissionMeta(TypedDict):
    task: str
    worker_id: str
    worker_type: str


def build_task_submission_meta(task: str, worker_id: str, worker_type: str | None = None) -> TaskSubmissionMeta:
    return {
        "task": task,
        "worker_id": worker_id,
        "worker_type": worker_type or task,
    }


def is_task_submission_meta(value: Any) -> TypeGuard[TaskSubmissionMeta]:
    if not isinstance(value, dict):
        return False
    return isinstance(value.get("task"), str) and isinstance(value.get("worker_id"), str) and isinstance(value.get("worker_type"), str)
