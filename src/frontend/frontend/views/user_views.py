from flask import render_template, request, Response
from flask_jwt_extended import get_jwt_identity
import json

from frontend.core_api import CoreApi
from frontend.models import Role, Organization
from frontend.data_persistence import DataPersistenceLayer
from frontend.models import User

from frontend.views.base_view import BaseView


class UserView(BaseView):
    model = User
    id_key = "user"
    htmx_template = "user/user_form.html"
    default_template = "user/index.html"
    base_route = "admin.users"
    edit_route = "admin.edit_user"

    @classmethod
    def get_extra_context(cls, object_id: int):
        dpl = DataPersistenceLayer()
        return {
            "organizations": dpl.get_objects(Organization),
            "roles": dpl.get_objects(Role),
            "current_user": get_jwt_identity(),
        }


def edit_user_view(user_id: int = 0):
    template = UserView.select_template()
    context = UserView.get_context(user_id)
    return render_template(template, **context)


def update_user_view(user_id: int = 0):
    return UserView.update_view(user_id)


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
