from typing import Any

from flask import session
from models.admin import Settings

from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger


ADMIN_WELCOME_TOUR_ID = "admin_welcome_v1"
ADMIN_ADVANCED_TOUR_ID = "admin_advanced_v1"
ADMIN_ONBOARDING_SESSION_KEY = "admin_onboarding"
ONBOARDING_COMPLETED_STATUS = "completed"


def _base_admin_onboarding_context() -> dict[str, bool | str]:
    return {
        "welcome_tour_id": ADMIN_WELCOME_TOUR_ID,
        "advanced_tour_id": ADMIN_ADVANCED_TOUR_ID,
        "welcome_completed": False,
        "advanced_completed": False,
    }


def is_onboarding_tour_completed(onboarding_tours: dict[str, str], tour_id: str) -> bool:
    return onboarding_tours.get(tour_id) == ONBOARDING_COMPLETED_STATUS


def needs_admin_onboarding(context: dict[str, bool | str] | None) -> bool:
    return bool(context and (not context.get("welcome_completed") or not context.get("advanced_completed")))


def _store_admin_onboarding_context(
    context: dict[str, bool | str] | None,
    *,
    needs_onboarding: bool | None = None,
) -> dict[str, bool | str] | None:
    needs = needs_admin_onboarding(context) if needs_onboarding is None else needs_onboarding
    session[ADMIN_ONBOARDING_SESSION_KEY] = {
        "needs_onboarding": needs,
        "context": context if needs else None,
    }
    return context if needs else None


def get_admin_onboarding_context() -> dict[str, bool | str] | None:
    try:
        settings = DataPersistenceLayer().get_first(Settings)
    except Exception:
        logger.exception("Failed to load admin onboarding settings")
        return None

    if not settings:
        return None

    onboarding_tours = settings.settings.onboarding_tours or {}
    context = _base_admin_onboarding_context()
    context["welcome_completed"] = is_onboarding_tour_completed(onboarding_tours, ADMIN_WELCOME_TOUR_ID)
    context["advanced_completed"] = is_onboarding_tour_completed(onboarding_tours, ADMIN_ADVANCED_TOUR_ID)
    return context


def get_cached_admin_onboarding_context() -> dict[str, bool | str] | None:
    cached = session.get(ADMIN_ONBOARDING_SESSION_KEY)
    if isinstance(cached, dict):
        if not cached.get("needs_onboarding"):
            return None
        context = cached.get("context")
        if isinstance(context, dict):
            return context

    return _store_admin_onboarding_context(get_admin_onboarding_context())


def reset_admin_onboarding_session() -> None:
    _store_admin_onboarding_context(_base_admin_onboarding_context(), needs_onboarding=True)


def clear_admin_onboarding_session() -> None:
    session.pop(ADMIN_ONBOARDING_SESSION_KEY, None)


def update_admin_onboarding_session_from_settings_payload(payload: dict[str, Any] | None, *, continue_onboarding: bool = False) -> None:
    settings_payload = payload.get("settings") if isinstance(payload, dict) else None
    onboarding_tours = settings_payload.get("onboarding_tours") if isinstance(settings_payload, dict) else None
    if not isinstance(onboarding_tours, dict):
        return

    cached = session.get(ADMIN_ONBOARDING_SESSION_KEY)
    context = cached.get("context") if isinstance(cached, dict) else None
    if not isinstance(context, dict):
        context = _base_admin_onboarding_context()

    if ADMIN_WELCOME_TOUR_ID in onboarding_tours:
        context["welcome_completed"] = onboarding_tours[ADMIN_WELCOME_TOUR_ID] == ONBOARDING_COMPLETED_STATUS
    if ADMIN_ADVANCED_TOUR_ID in onboarding_tours:
        context["advanced_completed"] = onboarding_tours[ADMIN_ADVANCED_TOUR_ID] == ONBOARDING_COMPLETED_STATUS

    needs_onboarding = continue_onboarding or needs_admin_onboarding(context)
    _store_admin_onboarding_context(context, needs_onboarding=needs_onboarding)
