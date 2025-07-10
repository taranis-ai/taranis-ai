import json
from typing import Any
from flask import render_template, request, Response
from flask_jwt_extended import get_jwt_identity

from frontend.core_api import CoreApi
from models.admin import Role, Organization, User
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count
from frontend.views.base_view import BaseView
from frontend.config import Config
from frontend.log import logger


class UserView(BaseView):
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
        roles = [int(role) for role in request.form.getlist("roles[]")]
        organization = int(request.form.get("organization", "0"))
        users = request.files.get("file")
        if not users or organization == 0:
            return cls.import_view("No file or organization provided")
        data = users.read()
        data = json.loads(data)
        for user in data["data"]:
            user["roles"] = roles
            user["organization"] = organization
        data = json.dumps(data["data"])

        response = CoreApi().import_users(json.loads(data))

        if not response:
            error = "Failed to import users"
            return cls.import_view(error)

        DataPersistenceLayer().invalidate_cache_by_object(User)
        return Response(status=200, headers={"HX-Refresh": "true"})

    @classmethod
    def export_view(cls):
        user_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_users(user_ids)

        if not core_resp:
            logger.debug(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "users_export.json")
