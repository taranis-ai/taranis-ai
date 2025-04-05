from flask import render_template, request, Response
from flask_jwt_extended import get_jwt_identity
import json

from frontend.core_api import CoreApi
from frontend.models import Role, Organization
from frontend.data_persistence import DataPersistenceLayer
from frontend.models import User
from frontend.router_helpers import is_htmx_request, parse_formdata


def import_users_view(error=None):
    organizations = DataPersistenceLayer().get_objects(Organization)
    roles = DataPersistenceLayer().get_objects(Role)

    return render_template("user/user_import.html", roles=roles, organizations=organizations, error=error)


def import_users_post_view():
    roles = [int(role) for role in request.form.getlist("roles[]")]
    organization = int(request.form.get("organization", "0"))
    users = request.files.get("file")
    if not users or organization == 0:
        return import_users_view("No file or organization provided")
    data = users.read()
    data = json.loads(data)
    for user in data["data"]:
        user["roles"] = roles
        user["organization"] = organization
    data = json.dumps(data["data"])

    response = CoreApi().import_users(json.loads(data))

    if not response:
        error = "Failed to import users"
        return import_users_view(error)

    DataPersistenceLayer().invalidate_cache_by_object(User)
    return Response(status=200, headers={"HX-Refresh": "true"})


def process_form_data(user_id: int):
    try:
        user = User(**parse_formdata(request.form))
        result = DataPersistenceLayer().store_object(user) if user_id == 0 else DataPersistenceLayer().update_object(user, user_id)
        return (user, None) if result.ok else (None, result.json().get("error"))
    except Exception as exc:
        return None, str(exc)


def select_template() -> str:
    return "user/user_form.html" if is_htmx_request() else "user/index.html"


def get_context(
    user_id: int,
    error: str | None = None,
    form_error: str | None = None,
    data_obj: User | None = None,
):
    dpl = DataPersistenceLayer()
    context = {
        "user_id": user_id,
        "organizations": dpl.get_objects(Organization),
        "roles": dpl.get_objects(Role),
        "error": error,
        "form_error": form_error,
    }
    if user_id != 0:
        context["current_user"] = get_jwt_identity()
        context["user"] = data_obj or dpl.get_object(User, user_id)
    return context


def edit_user_view(user_id: int = 0):
    template = select_template()
    context = get_context(user_id)
    return render_template(template, **context)


def update_user_view(user_id: int = 0):
    user_obj, error = process_form_data(user_id)
    if user_obj:
        return Response(status=200, headers={"HX-Refresh": "true"})
    template = select_template()
    context = get_context(user_id, error=error, data_obj=user_obj)
    return render_template(template, **context)
