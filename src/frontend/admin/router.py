from pydantic import BaseModel, ValidationError
from flask import Flask, render_template, Blueprint, request, Response, jsonify, redirect
from flask.json.provider import DefaultJSONProvider
from flask.views import MethodView
from flask_htmx import HTMX
from flask_jwt_extended import jwt_required
from swagger_ui import api_doc
import json

from admin.filters import human_readable_trigger
from admin.core_api import CoreApi
from admin.config import Config
from admin.cache import cache, add_user_to_cache, remove_user_from_cache, get_cached_users
from admin.models import Role, User, Organization, PagingData, Job
from admin.data_persistence import DataPersistenceLayer
from admin.log import logger
from admin.auth import get_jwt_identity, auth_required
from admin.router_helpers import is_htmx_request, parse_formdata, convert_query_params


class Dashboard(MethodView):
    def get(self):
        result = CoreApi().get_dashboard()

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("index.html", data=result)


class RolesAPI(MethodView):
    def get(self):
        result = DataPersistenceLayer().get_objects(Role)
        if result is None:
            return f"Failed to fetch roles from: {Config.TARANIS_CORE_URL}", 500

        return render_template("roles.html", roles=result)


class ScheduleAPI(MethodView):
    @jwt_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        try:
            q = PagingData(**query_params)
        except ValidationError as ve:
            return {"error": str(ve)}
        result = DataPersistenceLayer().get_objects(Job, q)

        if result is None:
            return f"Failed to fetch jobs from: {Config.TARANIS_CORE_URL}", 500

        return render_template("schedule/index.html", jobs=result)


class ScheduleJobDetailsAPI(MethodView):
    @jwt_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)


# create a users index view
class UsersAPI(MethodView):
    @jwt_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        try:
            q = PagingData(**query_params)
        except ValidationError as ve:
            return {"error": str(ve)}
        result = DataPersistenceLayer().get_objects(User, q)

        if result is None:
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        if is_htmx_request():
            return render_template("user/users_table.html", users=result)
        return render_template("user/index.html", users=result)

    @auth_required()
    def post(self):
        if is_htmx_request():
            logger.debug("Received htmx request")
        user = User(**parse_formdata(request.form))
        result = DataPersistenceLayer().store_object(user)
        if not result.ok:
            logger.debug(f"User back: {user.__dict__}")
            organizations = DataPersistenceLayer().get_objects(Organization)
            roles = DataPersistenceLayer().get_objects(Role)
            # add a static error message as test
            # user._errors['username'] = "Username already exists"

            return render_template(
                "user/user_form.html",
                organizations=organizations,
                roles=roles,
                action="new",
                user=user,
                error=result.json(),
                form_error={},
            ), result.status_code

        return Response(status=200, headers={"HX-Refresh": "true"})


class UpdateUser(MethodView):
    @jwt_required()
    def get(self, user_id: int):
        organizations = DataPersistenceLayer().get_objects(Organization)
        roles = DataPersistenceLayer().get_objects(Role)
        if user_id == 0:
            return render_template("user/user_form.html", organizations=organizations, roles=roles, action="new")
        user = DataPersistenceLayer().get_object(User, user_id)
        current_user = get_jwt_identity()
        return render_template("user/user_form.html", organizations=organizations, roles=roles, user=user, current_user=current_user)

    @jwt_required()
    def put(self, id):
        user = User(**parse_formdata(request.form))
        result = DataPersistenceLayer().update_object(user, id)
        if not result.ok:
            organizations = DataPersistenceLayer().get_objects(Organization)
            roles = DataPersistenceLayer().get_objects(Role)
            response = render_template(
                "user/user_form.html", user=user, error=result.content.decode(), organizations=organizations, roles=roles, action="edit"
            )
            return response, 200

        return Response(status=200, headers={"HX-Refresh": "true"})

    @jwt_required()
    def delete(self, user_id):
        result = DataPersistenceLayer().delete_object(User, user_id)
        return "error" if result == "error" else Response(status=200)


class NewUser(MethodView):
    @jwt_required()
    def get(self):
        organizations = DataPersistenceLayer().get_objects(Organization)
        roles = DataPersistenceLayer().get_objects(Role)
        return render_template("user/user_form.html", organizations=organizations, roles=roles, action="new")


class OrganizationsAPI(MethodView):
    @jwt_required()
    def get(self):
        result = DataPersistenceLayer().get_objects(Organization)
        if result is None:
            return f"Failed to fetch organization from: {Config.TARANIS_CORE_URL}", 500

        return render_template("organization/organizations.html", organizations=result)


class NewOrganization(MethodView):
    def get(self):
        return render_template("new_organization.html")


class InvalidateCache(MethodView):
    def get(self, suffix: str):
        keys = list(cache.cache._cache.keys())
        keys_to_delete = [key for key in keys if key.endswith(f"_{suffix}")]
        for key in keys_to_delete:
            cache.delete(key)

        return "Cache invalidated"


class ListCacheKeys(MethodView):
    def get(self):
        keys = cache.cache._cache.keys()
        return Response("<br>".join(keys))


class ListUserCache(MethodView):
    def get(self):
        return jsonify(get_cached_users())


class UserCache(MethodView):
    def post(self):
        user = request.json
        if not user:
            return {"error": "No data provided"}, 400
        add_user_to_cache(user)

    def delete(self):
        body = request.json
        if not body:
            return {"error": "No data provided"}, 400
        remove_user_from_cache(body["username"])


class TaranisJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        transformed_obj = self._transform(obj)
        return super().dumps(transformed_obj, **kwargs)

    def _transform(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump(exclude_none=True)
        elif isinstance(obj, list):
            return [self._transform(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._transform(value) for key, value in obj.items()}
        return obj


def handle_unauthorized(e):
    return redirect("/login", code=302)


class ExportImportUsers(MethodView):
    def get(self):
        user_ids = request.args.getlist("ids")

        response = CoreApi().export_users(user_ids)

        if not response:
            logger.debug(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return "Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get("Content-Type", "application/json"),
            headers={"Content-Disposition": response.headers.get("Content-Disposition", "attachment; filename=users_export.json")},
            status=response.status_code,
        )

    def post(self):
        file = request.files.get("file")
        if not file:
            return {"error": "No file provided"}, 400

        response = CoreApi().import_users(json.loads(file.read()))

        if not response:
            logger.debug(f"Failed to import users to: {Config.TARANIS_CORE_URL}")
            return "Failed to import users to: {Config.TARANIS_CORE_URL}", 500

        return Response(status=200)


def init(app: Flask):
    app.json_provider_class = TaranisJSONProvider
    app.json = app.json_provider_class(app)
    HTMX(app)
    app.register_error_handler(401, handle_unauthorized)

    api_doc(app, config_url=f"{Config.TARANIS_CORE_URL}/static/openapi3_1.yaml", url_prefix=f"{Config.APPLICATION_ROOT}/doc", editor=False)

    app.url_map.strict_slashes = False
    app.jinja_env.filters["human_readable"] = human_readable_trigger

    admin_bp = Blueprint("admin", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    admin_bp.add_url_rule("/", view_func=Dashboard.as_view("dashboard"))

    admin_bp.add_url_rule("/users", view_func=UsersAPI.as_view("users"))
    admin_bp.add_url_rule("/users/<int:user_id>", view_func=UpdateUser.as_view("edit_user"))
    admin_bp.add_url_rule("/export/users", view_func=ExportImportUsers.as_view("export_users"))
    admin_bp.add_url_rule("/import/users", view_func=ExportImportUsers.as_view("import_users"))

    admin_bp.add_url_rule("/schedule", view_func=ScheduleAPI.as_view("schedule"))
    admin_bp.add_url_rule("/schedule/job/<string:job_id>", view_func=ScheduleJobDetailsAPI.as_view("schedule_job_details"))

    admin_bp.add_url_rule("/organizations/", view_func=OrganizationsAPI.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/new", view_func=NewOrganization.as_view("new_organization"))

    admin_bp.add_url_rule("/login", view_func=UserCache.as_view("login"))
    admin_bp.add_url_rule("/logout", view_func=UserCache.as_view("logout"))
    # add a new route to invalidate cache specific to users
    admin_bp.add_url_rule("/invalidate_cache/<suffix>", view_func=InvalidateCache.as_view("invalidate_cache"))
    admin_bp.add_url_rule("/list_cache_keys", view_func=ListCacheKeys.as_view("list_cache_keys"))
    admin_bp.add_url_rule("/list_user_cache", view_func=ListUserCache.as_view("list_user_cache"))

    app.register_blueprint(admin_bp)
