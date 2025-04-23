from flask import Flask, render_template, Blueprint, request, Response
from flask.views import MethodView

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.models import Role, User, Organization, PagingData, Job, Dashboard
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required
from frontend.router_helpers import convert_query_params
from frontend.views.user_views import UserView
from frontend.views.organization_views import OrganizationView
from frontend.views.role_views import RoleView


class AdminDashboardAPI(MethodView):
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
        return UserView.list_view()

    @auth_required()
    def post(self):
        return UserView.update_view(object_id=0)


class UpdateUser(MethodView):
    @auth_required()
    def get(self, user_id: int = 0):
        return UserView.edit_view(object_id=user_id)

    @auth_required()
    def put(self, user_id: int):
        return UserView.update_view(object_id=user_id)

    @auth_required()
    def delete(self, user_id: int):
        result = DataPersistenceLayer().delete_object(User, user_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"}) if result else "error"


class OrganizationsAPI(MethodView):
    @auth_required()
    def get(self):
        return OrganizationView.list_view()

    @auth_required()
    def post(self):
        return OrganizationView.update_view(object_id=0)


class UpdateOrganization(MethodView):
    @auth_required()
    def get(self, organization_id: int):
        return OrganizationView.edit_view(object_id=organization_id)

    @auth_required()
    def put(self, organization_id: int):
        return OrganizationView.update_view(object_id=organization_id)

    @auth_required()
    def delete(self, organization_id: int):
        result = DataPersistenceLayer().delete_object(Organization, organization_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"})


class RolesAPI(MethodView):
    @auth_required()
    def get(self):
        return RoleView.list_view()

    @auth_required()
    def post(self):
        return RoleView.update_view(object_id=0)


class UpdateRole(MethodView):
    @auth_required()
    def get(self, role_id: int = 0):
        return RoleView.edit_view(object_id=role_id)

    @auth_required()
    def put(self, role_id):
        return RoleView.update_view(object_id=role_id)

    @auth_required()
    def delete(self, role_id):
        result = DataPersistenceLayer().delete_object(Role, role_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"})


class ExportUsers(MethodView):
    @auth_required()
    def get(self):
        user_ids = request.args.getlist("ids")

        core_resp = CoreApi().export_users(user_ids)

        if not core_resp:
            logger.debug(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "users_export.json")


class ImportUsers(MethodView):
    @auth_required()
    def get(self):
        return UserView.import_users_view()

    def post(self):
        return UserView.import_users_post_view()


def init(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/admin")

    admin_bp.add_url_rule("/", view_func=AdminDashboardAPI.as_view("dashboard"))

    admin_bp.add_url_rule("/users", view_func=UsersAPI.as_view("users"))
    admin_bp.add_url_rule("/users/<int:user_id>", view_func=UpdateUser.as_view("edit_user"))
    admin_bp.add_url_rule("/export/users", view_func=ExportUsers.as_view("export_users"))
    admin_bp.add_url_rule("/import/users", view_func=ImportUsers.as_view("import_users"))

    admin_bp.add_url_rule("/scheduler", view_func=ScheduleAPI.as_view("scheduler"))
    admin_bp.add_url_rule("/scheduler/job/<string:job_id>", view_func=ScheduleJobDetailsAPI.as_view("scheduler_job_details"))

    admin_bp.add_url_rule("/organizations", view_func=OrganizationsAPI.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/<int:organization_id>", view_func=UpdateOrganization.as_view("edit_organization"))

    admin_bp.add_url_rule("/roles", view_func=RolesAPI.as_view("roles"))
    admin_bp.add_url_rule("/roles/<int:role_id>", view_func=UpdateRole.as_view("edit_role"))

    app.register_blueprint(admin_bp)
