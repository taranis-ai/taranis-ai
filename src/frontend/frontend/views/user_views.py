from typing import Any
from flask import render_template, request
from flask_jwt_extended import current_user

from models.admin import User
from frontend.views.base_view import BaseView
from frontend.utils.form_data_parser import parse_formdata
from frontend.log import logger
from frontend.auth import auth_required


class UserView(BaseView):
    model = User
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
    def update_settings(cls, form_data: dict[str, Any]) -> tuple[str, int]:
        try:
            user = current_user
            if not user:
                return "User not found", 404

            parsed_data = parse_formdata(request.form)
            user = cls.model(**parsed_data)
            logger.debug(f"Updating user settings for user {user.model_dump()}")
            return "Settings updated successfully", 200
        except Exception as e:
            return f"Error updating settings: {str(e)}", 500

    def get(self, **kwargs) -> tuple[str, int]:
        return render_template("user_profile/profile.html", user=current_user), 200
