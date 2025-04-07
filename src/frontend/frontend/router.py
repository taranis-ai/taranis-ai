from flask import Flask, render_template, Blueprint, request, Response, jsonify
from flask.views import MethodView
from swagger_ui import api_doc
from flask_jwt_extended import set_access_cookies

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache import get_cached_users, list_cache_keys
from frontend.models import Role, User, Organization, PagingData, Job, Dashboard
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required
from frontend.router_helpers import is_htmx_request, parse_formdata, convert_query_params
from frontend.views.user_views import import_users_view, import_users_post_view, edit_user_view, update_user_view
from frontend.views.role_views import edit_role_view, update_role_view


class DashboardAPI(MethodView):
    @auth_required()
    def get(self):
        result = DataPersistenceLayer().get_objects(Dashboard)

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("dashboard/index.html", data=result[0])


class ScheduleAPI(MethodView):
    @auth_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        error = None
        result = None
        try:
            q = PagingData(**query_params)
            result = DataPersistenceLayer().get_objects(Job, q)
        except Exception as ve:
            error = str(ve)

        return render_template("schedule/index.html", jobs=result, error=error)


class ScheduleJobDetailsAPI(MethodView):
    @auth_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)


class UsersAPI(MethodView):
    @auth_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        error = None
        result = None
        try:
            q = PagingData(**query_params)
            result = DataPersistenceLayer().get_objects(User, q)
        except Exception as ve:
            error = str(ve)

        if is_htmx_request():
            return render_template("user/users_table.html", users=result, error=error)
        return render_template("user/index.html", users=result, error=error)

    @auth_required()
    def post(self):
        return update_user_view(user_id=0)


class UpdateUser(MethodView):
    @auth_required()
    def get(self, user_id: int = 0):
        return edit_user_view(user_id=user_id)

    @auth_required()
    def put(self, user_id):
        return update_user_view(user_id=user_id)

    @auth_required()
    def delete(self, user_id):
        result = DataPersistenceLayer().delete_object(User, user_id)
        return "error" if result == "error" else Response(status=result.status_code, headers={"HX-Refresh": "true"})


class OrganizationsAPI(MethodView):
    @auth_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        error = None
        result = None
        try:
            q = PagingData(**query_params)
            result = DataPersistenceLayer().get_objects(Organization, q)
        except Exception as ve:
            error = str(ve)

        if is_htmx_request():
            return render_template("organization/organizations_table.html", organizations=result, error=error)

        return render_template("organization/index.html", organizations=result, error=error)

    @auth_required()
    def post(self):
        organization = Organization(**parse_formdata(request.form))
        result = DataPersistenceLayer().store_object(organization)
        if not result.ok:
            _error = result.json().get("error")
            logger.warning(f"Failed to store organization: {_error}")

            return render_template(
                "organization/organization_form.html",
                organization=organization,
                error=_error,
                form_error={},
            ), result.status_code

        return Response(status=200, headers={"HX-Refresh": "true"})


class UpdateOrganization(MethodView):
    @auth_required()
    def get(self, organization_id: int):
        template = "organization/organization_form.html" if is_htmx_request() else "organization/organization_edit.html"
        if organization_id == 0:
            return render_template(template)
        organization = DataPersistenceLayer().get_object(Organization, organization_id)
        return render_template(template, organization=organization)

    @auth_required()
    def put(self, organization_id):
        organization = Organization(**parse_formdata(request.form))
        result = DataPersistenceLayer().update_object(organization, organization_id)
        if not result.ok:
            response = render_template("organization/organization_form.html", organization=organization)
            return response, result.status_code

        return Response(status=result.status_code, headers={"HX-Refresh": "true"})

    @auth_required()
    def delete(self, organization_id):
        result = DataPersistenceLayer().delete_object(Organization, organization_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"})


class RolesAPI(MethodView):
    @auth_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        error = None
        result = None
        try:
            q = PagingData(**query_params)
            result = DataPersistenceLayer().get_objects(Role, q)
        except Exception as ve:
            error = str(ve)

        if is_htmx_request():
            return render_template("role/roles_table.html", roles=result, error=error)
        return render_template("role/index.html", roles=result, error=error)

    @auth_required()
    def post(self):
        return update_role_view(role_id=0)


class UpdateRole(MethodView):
    @auth_required()
    def get(self, role_id: int = 0):
        return edit_role_view(role_id=role_id)

    @auth_required()
    def put(self, role_id):
        return update_role_view(role_id=role_id)

    @auth_required()
    def delete(self, role_id):
        result = DataPersistenceLayer().delete_object(Role, role_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"})


class InvalidateCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self, suffix: str):
        if not suffix:
            return {"error": "No suffix provided"}, 400
        DataPersistenceLayer().invalidate_cache(suffix)
        return "Cache invalidated"


class ListCacheKeys(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return Response("<br>".join(list_cache_keys()))


class ListUserCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return jsonify(get_cached_users())


class LoginView(MethodView):
    def get(self):
        return render_template("login/index.html")

    def post(self):
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("login/index.html", error="Username and password are required"), 400

        core_response = CoreApi().login(username, password)

        jwt_token = core_response.json().get("access_token")

        logger.debug(f"Login response: {jwt_token}")

        if not core_response.ok:
            return render_template("login/index.html", error=core_response.json().get("error")), core_response.status_code

        response = Response(status=core_response.status_code, headers={"HX-Redirect": "/frontend/"})
        set_access_cookies(response, jwt_token)

        return response


class ExportUsers(MethodView):
    @auth_required()
    def get(self):
        user_ids = request.args.getlist("ids")

        response = CoreApi().export_users(user_ids)

        if not response:
            logger.debug(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get("Content-Type", "application/json"),
            headers={"Content-Disposition": response.headers.get("Content-Disposition", "attachment; filename=users_export.json")},
            status=response.status_code,
        )


class ImportUsers(MethodView):
    @auth_required()
    def get(self):
        return import_users_view()

    def post(self):
        return import_users_post_view()


def init(app: Flask):
    api_doc(app, config_url=f"{Config.TARANIS_CORE_URL}/static/openapi3_1.yaml", url_prefix=f"{Config.APPLICATION_ROOT}/doc", editor=False)

    admin_bp = Blueprint("admin", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    admin_bp.add_url_rule("/", view_func=DashboardAPI.as_view("dashboard"))

    admin_bp.add_url_rule("/users", view_func=UsersAPI.as_view("users"))
    admin_bp.add_url_rule("/users/<int:user_id>", view_func=UpdateUser.as_view("edit_user"))
    admin_bp.add_url_rule("/export/users", view_func=ExportUsers.as_view("export_users"))
    admin_bp.add_url_rule("/import/users", view_func=ImportUsers.as_view("import_users"))

    admin_bp.add_url_rule("/schedule", view_func=ScheduleAPI.as_view("schedule"))
    admin_bp.add_url_rule("/schedule/job/<string:job_id>", view_func=ScheduleJobDetailsAPI.as_view("schedule_job_details"))

    admin_bp.add_url_rule("/organizations", view_func=OrganizationsAPI.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/<int:organization_id>", view_func=UpdateOrganization.as_view("edit_organization"))

    admin_bp.add_url_rule("/roles/", view_func=RolesAPI.as_view("roles"))
    admin_bp.add_url_rule("/roles/<int:role_id>", view_func=UpdateRole.as_view("edit_role"))

    admin_bp.add_url_rule("/login", view_func=LoginView.as_view("login"))
    # add a new route to invalidate cache specific to users
    admin_bp.add_url_rule("/invalidate_cache/<suffix>", view_func=InvalidateCache.as_view("invalidate_cache"))
    admin_bp.add_url_rule("/list_cache_keys", view_func=ListCacheKeys.as_view("list_cache_keys"))
    admin_bp.add_url_rule("/list_user_cache", view_func=ListUserCache.as_view("list_user_cache"))

    app.register_blueprint(admin_bp)
