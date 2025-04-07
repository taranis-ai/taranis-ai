from flask import render_template, request
from flask import Response

from frontend.models import Role, Permissions
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata


def process_form_data(role_id: int):
    try:
        role = Role(**parse_formdata(request.form))
        result = DataPersistenceLayer().store_object(role) if role_id == 0 else DataPersistenceLayer().update_object(role, role_id)
        return (role, None) if result.ok else (None, result.json().get("error"))
    except Exception as exc:
        return None, str(exc)


def select_template() -> str:
    return "role/role_form.html" if is_htmx_request() else "role/role_edit.html"


def get_context(
    role_id: int,
    error: str | None = None,
    form_error: str | None = None,
    role_obj: Role | None = None,
):
    dpl = DataPersistenceLayer()
    context = {
        "permissions": [p.model_dump() for p in DataPersistenceLayer().get_objects(Permissions)],
        "error": error,
        "form_error": form_error,
    }
    if role_id != 0:
        context["role"] = role_obj or dpl.get_object(Role, role_id)
    return context


def edit_role_view(role_id: int = 0):
    template = select_template()
    context = get_context(role_id)
    return render_template(template, **context)


def update_role_view(role_id: int = 0):
    data_obj, error = process_form_data(role_id)
    if data_obj:
        return Response(status=200, headers={"HX-Refresh": "true"})
    template = select_template()
    context = get_context(role_id, error=error, role_obj=data_obj)
    return render_template(template, **context)
