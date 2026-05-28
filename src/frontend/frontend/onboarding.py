from typing import Any

from flask import session
from models.admin import Settings
from pydantic import ValidationError
from requests import RequestException

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


def _store_admin_onboarding_context(context: dict[str, bool | str] | None) -> dict[str, bool | str] | None:
    session[ADMIN_ONBOARDING_SESSION_KEY] = context if isinstance(context, dict) else None
    return session[ADMIN_ONBOARDING_SESSION_KEY]


def get_admin_onboarding_context() -> dict[str, bool | str] | None:
    try:
        settings = DataPersistenceLayer().get_first(Settings)
    except (RequestException, ValueError, ValidationError) as error:
        logger.exception(f"Failed to load admin onboarding settings: {error}")
        return None

    if not settings:
        return None

    onboarding_tours = settings.settings.onboarding_tours or {}
    context = _base_admin_onboarding_context()
    context["welcome_completed"] = is_onboarding_tour_completed(onboarding_tours, ADMIN_WELCOME_TOUR_ID)
    context["advanced_completed"] = is_onboarding_tour_completed(onboarding_tours, ADMIN_ADVANCED_TOUR_ID)
    return context


def get_cached_admin_onboarding_context() -> dict[str, bool | str] | None:
    if ADMIN_ONBOARDING_SESSION_KEY in session:
        cached = session.get(ADMIN_ONBOARDING_SESSION_KEY)
        return cached if isinstance(cached, dict) else None

    return _store_admin_onboarding_context(get_admin_onboarding_context())


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
