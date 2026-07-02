import json
from typing import Any

from flask import flash, render_template, request
from flask_jwt_extended import get_jwt_identity
from models.admin import Organization, Role, User

from frontend.auth import admin_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


class UserView(AdminBaseView):
    model = User
    icon = "user"
    _index = 20

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        base_context["organizations"] = dpl.get_objects(Organization)
        base_context["roles"] = dpl.get_objects(Role)
        base_context["current_user"] = get_jwt_identity()
        return base_context

    @classmethod
    def get_columns(cls):
        return [
            {"title": "username", "field": "username", "sortable": True, "renderer": None},
            {"title": "name", "field": "name", "sortable": True, "renderer": None},
            {"title": "roles", "field": "roles", "sortable": False, "renderer": render_count, "render_args": {"field": "roles"}},
            {
                "title": "permissions",
                "field": "permissions",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "permissions"},
            },
        ]

    @classmethod
    def import_view(cls, error=None):
        organizations = DataPersistenceLayer().get_objects(Organization)
        roles = DataPersistenceLayer().get_objects(Role)

        return render_template(
            f"{cls.model_name().lower()}/{cls.model_name().lower()}_import.html", roles=roles, organizations=organizations, error=error
        )

    @classmethod
    def import_post_view(cls):
        roles = request.form.getlist("roles[]")
        organization = request.form.get("organization", "0")
        users = request.files.get("file")
        if not users or organization in {"0", ""}:
            return cls.import_view("No file or organization provided")
        try:
            data = json.loads(users.read())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return cls.render_response_notification({"error": "Invalid JSON file"}), 400

        if not isinstance(data, dict) or data.get("version") != 1:
            return cls.render_response_notification({"error": "Invalid user import file format"}), 400

        import_users = data.get("data") if isinstance(data, dict) else None
        if not isinstance(import_users, list):
            return cls.render_response_notification({"error": "Invalid user import file format"}), 400

        for user in import_users:
            if not isinstance(user, dict):
                return cls.render_response_notification({"error": "Invalid user import file format"}), 400
            user["roles"] = roles
            user["organization"] = organization
        response = CoreApi().import_users(import_users)

        if response is None:
            return cls.render_response_notification({"error": "Failed to import users"}), 500

        if not response.ok:
            return cls.get_notification_from_response(response), response.status_code or 500

        response_payload = response.json()
        if response_payload.get("skipped_count", 0) > 0:
            flash(response_payload.get("message", "User import completed with skipped users"), "warning")
        else:
            cls.add_flash_notification(response_payload)
        return cls.redirect_htmx(cls.get_base_route())

    @classmethod
    @admin_required()
    def export_view(cls):
        user_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_users({"ids": user_ids})

        if not core_resp:
            logger.warning(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "users_export.json")
