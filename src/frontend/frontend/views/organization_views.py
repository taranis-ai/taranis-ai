from flask import render_template, request
from flask import Response

from frontend.models import Organization
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata


def process_form_data(organization_id: int):
    try:
        organization = Organization(**parse_formdata(request.form))
        result = (
            DataPersistenceLayer().store_object(organization)
            if organization_id == 0
            else DataPersistenceLayer().update_object(organization, organization_id)
        )
        return (organization, None) if result.ok else (None, result.json().get("error"))
    except Exception as exc:
        return None, str(exc)


def select_template() -> str:
    return "role/role_form.html" if is_htmx_request() else "role/index.html"


def get_context(
    organization_id: int,
    error: str | None = None,
    form_error: str | None = None,
    data_obj: Organization | None = None,
):
    dpl = DataPersistenceLayer()
    context = {
        "organization_id": organization_id,
        "error": error,
        "form_error": form_error,
    }
    if organization_id != 0:
        context["organization"] = data_obj or dpl.get_object(Organization, organization_id)
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
    context = get_context(role_id, error=error, data_obj=data_obj)
    return render_template(template, **context)
