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

    @classmethod
    def get_context(
        cls, object_id: int, error: str | None = None, form_error: str | None = None, data_obj=None, extra_context: dict | None = None
    ):
        dpl = DataPersistenceLayer()
        extra_context = {"permissions": [p.model_dump() for p in dpl.get_objects(Permissions)]}
        return super().get_context(object_id, error, form_error, data_obj, extra_context)


def edit_role_view(role_id: int = 0):
    template = RoleView.select_template()
    context = RoleView.get_context(role_id)
    return render_template(template, **context)


def update_role_view(role_id: int = 0):
    return RoleView.update_view(role_id)
