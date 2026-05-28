from typing import Any

from flask import session
from models.user import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_WELCOME_TOUR_ID,
    ONBOARDING_COMPLETED_STATUS,
    ONBOARDING_SCOPE_GLOBAL,
    USER_PRODUCT_OVERVIEW_TASK_ID,
)


ADMIN_ONBOARDING_SESSION_KEY = "admin_onboarding"
ADMIN_ONBOARDING_TASK_IDS = (ADMIN_WELCOME_TOUR_ID, ADMIN_ADVANCED_TOUR_ID)
ONBOARDING_TASK_ORDER = (ADMIN_WELCOME_TOUR_ID, ADMIN_ADVANCED_TOUR_ID, USER_PRODUCT_OVERVIEW_TASK_ID)


def _base_admin_onboarding_context() -> dict[str, bool | str]:
    return {
        "welcome_tour_id": ADMIN_WELCOME_TOUR_ID,
        "advanced_tour_id": ADMIN_ADVANCED_TOUR_ID,
        "welcome_completed": False,
        "advanced_completed": False,
    }


def _user_permissions(user: Any) -> set[str]:
    return set(getattr(user, "permissions", None) or [])


def _has_admin_onboarding_access(user: Any) -> bool:
    permissions = _user_permissions(user)
    return "ALL" in permissions or "ADMIN_OPERATIONS" in permissions


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


def is_onboarding_tour_completed(onboarding_tours: dict[str, str], tour_id: str) -> bool:
    return onboarding_tours.get(tour_id) == ONBOARDING_COMPLETED_STATUS


def needs_admin_onboarding(context: dict[str, bool | str] | None) -> bool:
    return bool(context and (not context.get("welcome_completed") or not context.get("advanced_completed")))


def _store_admin_onboarding_context(context: dict[str, bool | str] | None) -> dict[str, bool | str] | None:
    session[ADMIN_ONBOARDING_SESSION_KEY] = context if isinstance(context, dict) else None
    return session[ADMIN_ONBOARDING_SESSION_KEY]


def _admin_context_from_pending_tasks(pending_tasks: list[dict[str, str]]) -> dict[str, bool | str]:
    pending_task_ids = {task["id"] for task in pending_tasks if task.get("scope") == ONBOARDING_SCOPE_GLOBAL}
    context = _base_admin_onboarding_context()
    context["welcome_completed"] = ADMIN_WELCOME_TOUR_ID not in pending_task_ids
    context["advanced_completed"] = ADMIN_ADVANCED_TOUR_ID not in pending_task_ids
    return context


def _pending_admin_tasks_from_context(context: dict[str, bool | str] | None) -> list[dict[str, str]]:
    if not isinstance(context, dict):
        return []

    tasks: list[dict[str, str]] = []
    if not context.get("welcome_completed"):
        tasks.append({"id": ADMIN_WELCOME_TOUR_ID, "scope": ONBOARDING_SCOPE_GLOBAL})
    if not context.get("advanced_completed"):
        tasks.append({"id": ADMIN_ADVANCED_TOUR_ID, "scope": ONBOARDING_SCOPE_GLOBAL})
    return tasks


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

    if ADMIN_ONBOARDING_SESSION_KEY in session and _has_admin_onboarding_access(user):
        pending_tasks = [task for task in pending_tasks if task["id"] not in ADMIN_ONBOARDING_TASK_IDS]
        session_context = session.get(ADMIN_ONBOARDING_SESSION_KEY)
        pending_tasks.extend(_pending_admin_tasks_from_context(session_context if isinstance(session_context, dict) else None))

    return _sort_onboarding_tasks(pending_tasks)


def get_admin_onboarding_context(user: Any) -> dict[str, bool | str] | None:
    if not user or not _has_admin_onboarding_access(user):
        return None
    return _admin_context_from_pending_tasks(pending_onboarding_tasks_for_template(user))


def get_cached_admin_onboarding_context(user: Any) -> dict[str, bool | str] | None:
    if ADMIN_ONBOARDING_SESSION_KEY in session:
        cached = session.get(ADMIN_ONBOARDING_SESSION_KEY)
        return cached if isinstance(cached, dict) else None

    return get_admin_onboarding_context(user)


def reset_admin_onboarding_session() -> None:
    _store_admin_onboarding_context(_base_admin_onboarding_context())


def clear_admin_onboarding_session() -> None:
    session.pop(ADMIN_ONBOARDING_SESSION_KEY, None)


def update_admin_onboarding_session_from_settings_payload(payload: dict[str, Any] | None, *, continue_onboarding: bool = False) -> None:
    reset_requested = isinstance(payload, dict) and payload.get("reset_onboarding_tours") in {True, "true", "1", "on"}
    if reset_requested:
        _store_admin_onboarding_context(_base_admin_onboarding_context())
        return

    settings_payload = payload.get("settings") if isinstance(payload, dict) else None
    onboarding_tours = settings_payload.get("onboarding_tours") if isinstance(settings_payload, dict) else None
    if not isinstance(onboarding_tours, dict):
        return

    cached = session.get(ADMIN_ONBOARDING_SESSION_KEY)
    context = cached if isinstance(cached, dict) else None
    if not isinstance(context, dict):
        context = _base_admin_onboarding_context()

    if ADMIN_WELCOME_TOUR_ID in onboarding_tours:
        context["welcome_completed"] = onboarding_tours[ADMIN_WELCOME_TOUR_ID] == ONBOARDING_COMPLETED_STATUS
    if ADMIN_ADVANCED_TOUR_ID in onboarding_tours:
        context["advanced_completed"] = onboarding_tours[ADMIN_ADVANCED_TOUR_ID] == ONBOARDING_COMPLETED_STATUS

    _store_admin_onboarding_context(context if continue_onboarding or needs_admin_onboarding(context) else None)
