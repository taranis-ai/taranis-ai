from typing import Any

from models.admin import Role, Permission
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView
from frontend.filters import render_count
from frontend.log import logger
from frontend.views.admin_mixin import AdminMixin


class RoleView(AdminMixin, BaseView):
    model = Role
    icon = "user-group"
    _index = 40

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        try:
            dpl = DataPersistenceLayer()
            base_context["permissions"] = [p.model_dump() for p in dpl.get_objects(Permission)]
        except Exception:
            logger.exception("Error retrieving permissions")
        return base_context

    @classmethod
    def get_columns(cls):
        columns = super().get_columns()
        return columns + [
            {
                "title": "Permissions",
                "field": "permissions",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "permissions"},
            }
        ]
