from models.admin import Role, Permission
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView
from frontend.filters import permissions_count


class RoleView(BaseView):
    model = Role
    icon = "user-group"
    _index = 40

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        return {"permissions": [p.model_dump() for p in dpl.get_objects(Permission)]}

    @classmethod
    def get_columns(cls):
        columns = super().get_columns()
        return columns + [{"title": "Permissions", "field": "permissions", "sortable": False, "renderer": permissions_count}]
