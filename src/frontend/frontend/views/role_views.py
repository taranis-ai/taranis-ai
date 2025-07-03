from typing import Any

from models.admin import Role, Permission
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView
from frontend.filters import permissions_count


class RoleView(BaseView):
    model = Role
    icon = "user-group"
    _index = 40

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        base_context["permissions"] = [p.model_dump() for p in dpl.get_objects(Permission)]
        return base_context

    @classmethod
    def get_columns(cls):
        columns = super().get_columns()
        return columns + [
            {
                "title": "Permissions",
                "field": "permissions",
                "sortable": False,
                "renderer": permissions_count,
            }
        ]
