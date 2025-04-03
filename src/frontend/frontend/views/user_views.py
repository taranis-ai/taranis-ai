from flask import render_template, request, Response
from flask_jwt_extended import get_jwt_identity
import json

from frontend.core_api import CoreApi
from frontend.models import Role, Organization
from frontend.data_persistence import DataPersistenceLayer
from frontend.models import User
from frontend.router_helpers import is_htmx_request


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


def edit_user_view(user_id: int, error=None, form_error=None):
    template = "user/user_form.html" if is_htmx_request() else "user/user_edit.html"
    organizations = DataPersistenceLayer().get_objects(Organization)
    roles = DataPersistenceLayer().get_objects(Role)
    if user_id == 0:
        return render_template(template, organizations=organizations, roles=roles)
    user = DataPersistenceLayer().get_object(User, user_id)
    current_user = get_jwt_identity()
    return render_template(
        template, organizations=organizations, roles=roles, user=user, current_user=current_user, error=error, form_error=form_error
    )
