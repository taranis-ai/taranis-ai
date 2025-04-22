# role_views.py
from flask import render_template
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

    @classmethod
    def edit_role_view(cls, role_id: int = 0):
        template = RoleView.get_update_template()
        context = RoleView.get_update_context(role_id)
        return render_template(template, **context)

    @classmethod
    def update_role_view(cls, role_id: int = 0):
        return RoleView.update_view(role_id)
