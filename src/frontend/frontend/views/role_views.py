# role_views.py
from flask import render_template
from frontend.models import Role, Permissions
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class RoleView(BaseView):
    model = Role
    id_key = "role"
    htmx_template = "role/role_form.html"
    default_template = "role/index.html"
    base_route = "admin.roles"
    edit_route = "admin.edit_role"

    @classmethod
    def get_extra_context(cls, object_id: int):
        dpl = DataPersistenceLayer()
        return {"permissions": [p.model_dump() for p in dpl.get_objects(Permissions)]}


def edit_role_view(role_id: int = 0):
    template = RoleView.select_template()
    extra_context = RoleView.get_extra_context(role_id)
    context = RoleView.get_context(role_id, extra_context=extra_context)
    return render_template(template, **context)


def update_role_view(role_id: int = 0):
    extra_context = RoleView.get_extra_context(role_id)
    return RoleView.update_view(role_id, extra_context=extra_context)
