from typing import Any

from models.user import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_WELCOME_TOUR_ID,
    USER_PRODUCT_OVERVIEW_TASK_ID,
)


ONBOARDING_TASK_ORDER = (ADMIN_WELCOME_TOUR_ID, ADMIN_ADVANCED_TOUR_ID, USER_PRODUCT_OVERVIEW_TASK_ID)


def _task_to_dict(task: Any) -> dict[str, str] | None:
    if hasattr(task, "model_dump"):
        task = task.model_dump(mode="json")
    if not isinstance(task, dict):
        return None
    task_id = task.get("id")
    scope = task.get("scope")
    if isinstance(task_id, str) and isinstance(scope, str):
        return {"id": task_id, "scope": scope}
    return None


def _sort_onboarding_tasks(tasks: list[dict[str, str]]) -> list[dict[str, str]]:
    order = {task_id: index for index, task_id in enumerate(ONBOARDING_TASK_ORDER)}
    return sorted(tasks, key=lambda task: (order.get(task["id"], len(order)), task["id"]))


def pending_onboarding_tasks_for_template(user: Any) -> list[dict[str, str]]:
    if not user:
        return []

    pending_tasks: list[dict[str, str]] = []
    for task in getattr(user, "pending_onboarding_tasks", None) or []:
        if task_dict := _task_to_dict(task):
            pending_tasks.append(task_dict)

    return _sort_onboarding_tasks(pending_tasks)
