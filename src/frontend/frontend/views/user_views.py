from typing import Any

from flask import render_template, request
from flask.typing import ResponseReturnValue
from flask_babel import gettext
from flask_jwt_extended import current_user
from models.user import ProfileSettings, UserProfile
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required, update_current_user_cache
from frontend.core_api import CoreApi
from frontend.i18n import get_supported_language_options, get_timezone_options
from frontend.log import logger
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.views.base_view import BaseView


class UserProfileView(BaseView):
    model = UserProfile
    icon = "user"
    _index = 20

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        base_context["current_user"] = current_user
        return base_context

    @classmethod
    @auth_required()
    def get_settings_view(cls):
        return render_template("user_profile/settings.html", **cls._settings_context())

    @classmethod
    @auth_required()
    def change_password(cls):
        result = CoreApi().api_post("/auth/change_password", json_data=request.form)
        if result is not None and result.ok:
            return cls.get_notification_from_response(result, oob=False)

        error_message = None
        if result is not None:
            try:
                payload = result.json() or {}
                error_message = payload.get("error") or payload.get("message")
            except Exception:
                error_message = result.text
        if not error_message:
            error_message = gettext("Failed to change password.")
        logger.error(error_message)
        return (
            render_template("notification/index.html", notification={"message": error_message, "error": True}, oob=False),
            200,
        )

    @classmethod
    @auth_required()
    def post_settings_view(cls):
        core_response, error = cls.process_form_data("0")
        if not core_response or error:
            return render_template(
                "user_profile/settings.html",
                **cls._settings_context(notification={"message": error or gettext("Failed to update profile settings."), "error": True}),
            ), 400

        notification_response = cls.get_notification_from_dict(core_response)
        updated_user = update_current_user_cache() or current_user
        logger.debug(f"Profile settings updated: {core_response}")

        return render_template(
            "user_profile/settings.html",
            **cls._settings_context(user=updated_user),
            notification=notification_response,
        ), 200

    @classmethod
    def _settings_context(cls, **extra: Any) -> dict[str, Any]:
        context = {
            "user": extra.pop("user", current_user),
            "language_options": get_supported_language_options(),
            "timezone_options": get_timezone_options(),
        }
        context.update(extra)
        return context

    @classmethod
    def store_form_data(cls, processed_data: dict[str, Any], object_id: str = "0"):
        try:
            if not processed_data:
                return {"message": "Profile unchanged", "user_profile": cls._get_current_profile_data()}, None
            payload = cls._validated_profile_payload(processed_data)
            result = CoreApi().api_post(ProfileSettings._core_endpoint, json_data=payload)
            return (result.json(), None) if result.ok else (None, result.json())
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        if form_data.pop("reset_onboarding_tasks", None) == "true":
            form_data["onboarding_tasks"] = {}
        return form_data

    @classmethod
    def _validated_profile_payload(cls, updates: dict[str, Any]) -> dict[str, Any]:
        validated = ProfileSettings(**cls._get_merged_profile_data(updates)).model_dump(mode="json")
        return {key: validated[key] for key in updates}

    @classmethod
    def _get_current_profile_data(cls) -> dict[str, Any]:
        profile = getattr(current_user, "profile", None)
        if profile is not None and hasattr(profile, "model_dump"):
            return profile.model_dump(mode="json")
        if isinstance(profile, dict):
            return dict(profile)
        return {}

    @classmethod
    def _get_merged_profile_data(cls, updates: dict[str, Any]) -> dict[str, Any]:
        current_profile = cls._get_current_profile_data()
        merged_updates = dict(updates)
        onboarding_updates = updates.get("onboarding_tasks")
        current_onboarding_tasks = current_profile.get("onboarding_tasks")
        if isinstance(onboarding_updates, dict) and onboarding_updates and isinstance(current_onboarding_tasks, dict):
            merged_updates["onboarding_tasks"] = {**current_onboarding_tasks, **onboarding_updates}
        return {**current_profile, **merged_updates}

    def get(self, **kwargs: Any) -> ResponseReturnValue:
        return render_template("user_profile/profile.html", user=current_user), 200

    def post(self, *args: Any, **kwargs: Any) -> ResponseReturnValue:
        return self.post_settings_view()
