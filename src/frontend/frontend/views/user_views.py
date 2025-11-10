from typing import Any
from flask import render_template, request
from flask_jwt_extended import current_user
from pydantic import ValidationError
from werkzeug.wrappers import Response

from models.user import UserProfile, ProfileSettings
from frontend.views.base_view import BaseView
from frontend.log import logger
from frontend.auth import auth_required, update_current_user_cache
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.core_api import CoreApi


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
        LANGUAGE_OPTIONS = [
            {"id": "en", "name": "English"},
        ]
        return render_template("user_profile/settings.html", user=current_user, language_options=LANGUAGE_OPTIONS)

    @classmethod
    @auth_required()
    def change_password(cls):
        if result := CoreApi().api_post("/auth/change_password", json_data=request.form):
            return cls.get_notification_from_response(result)
        logger.error("Failed to change password.")
        return render_template(
            "user_profile/settings.html", user=current_user, notification={"message": "Failed to change password.", "error": True}
        ), 200

    @classmethod
    @auth_required()
    def post_settings_view(cls):
        LANGUAGE_OPTIONS = [
            {"id": "en", "name": "English"},
        ]
        core_response, error = cls.process_form_data(0)
        if not core_response or error:
            return render_template(
                "user_profile/settings.html",
                **cls.get_update_context(0, error=error),
            ), 400

        notification_response = cls.get_notification_from_dict(core_response)
        update_current_user_cache()
        logger.debug(f"Profile settings updated: {core_response}")

        return render_template(
            "user_profile/settings.html", user=current_user, language_options=LANGUAGE_OPTIONS, notification=notification_response
        ), 200

    @classmethod
    def store_form_data(cls, processed_data: dict[str, Any], object_id: int | str = 0):
        try:
            obj = ProfileSettings(**processed_data)
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj)
            return (result.json(), None) if result.ok else (None, result.json())
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    def get(self, **kwargs) -> tuple[str, int]:
        return render_template("user_profile/profile.html", user=current_user), 200

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        return self.post_settings_view()
