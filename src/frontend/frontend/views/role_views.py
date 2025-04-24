# role_views.py
from frontend.models import Role, Permissions
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class RoleView(BaseView):
    model = Role
    htmx_list_template = "role/roles_table.html"
    htmx_update_template = "role/role_form.html"
    default_template = "role/index.html"
    base_route = "admin.roles"
    edit_route = "admin.edit_role"

    @classmethod
    def get_extra_context(cls, object_id: int):
        dpl = DataPersistenceLayer()
        return {"permissions": [p.model_dump() for p in dpl.get_objects(Permissions)]}
