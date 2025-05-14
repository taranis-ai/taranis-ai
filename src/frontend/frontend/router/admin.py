from flask import Flask, render_template, Blueprint, request, Response
from flask.views import MethodView
from models.admin import Role, Job, Dashboard

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache_models import PagingData
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required
from frontend.router_helpers import convert_query_params
from frontend.views.user_views import UserView
from frontend.views.organization_views import OrganizationView
from frontend.views.role_views import RoleView
from frontend.views.acl_views import ACLView
from frontend.views.worker_views import WorkerView
from frontend.views.word_list_views import WordListView
from frontend.views.source_groups_views import SourceGroupView


class AdminDashboardAPI(MethodView):
    @auth_required()
    def get(self):
        result = DataPersistenceLayer().get_objects(Dashboard)

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("admin_dashboard/index.html", data=result[0])


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
        return UserView.delete_view(object_id=user_id)


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


class OrganizationsAPI(MethodView):
    @auth_required()
    def get(self):
        return OrganizationView.list_view()

    @auth_required()
    def post(self):
        return OrganizationView.update_view(object_id=0)

    @auth_required()
    def delete(self):
        if object_ids := request.form.getlist("ids"):
            return OrganizationView.delete_multiple_view(object_ids=object_ids)
        return Response(status=400, headers={"HX-Refresh": "true"})


class UpdateOrganization(MethodView):
    @auth_required()
    def get(self, organization_id: int):
        return OrganizationView.edit_view(object_id=organization_id)

    @auth_required()
    def put(self, organization_id: int):
        return OrganizationView.update_view(object_id=organization_id)

    @auth_required()
    def delete(self, organization_id: int):
        return OrganizationView.delete_view(object_id=organization_id)


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


class ACLsAPI(MethodView):
    @auth_required()
    def get(self):
        return ACLView.list_view()

    @auth_required()
    def post(self):
        return ACLView.update_view(object_id=0)


class UpdateACL(MethodView):
    @auth_required()
    def get(self, acl_id: int = 0):
        return ACLView.edit_view(object_id=acl_id)

    @auth_required()
    def put(self, acl_id):
        return ACLView.update_view(object_id=acl_id)

    @auth_required()
    def delete(self, acl_id):
        return ACLView.delete_view(object_id=acl_id)


class WorkersAPI(MethodView):
    @auth_required()
    def get(self):
        return WorkerView.list_view()

    @auth_required()
    def post(self):
        return WorkerView.update_view(object_id=0)


class UpdateWorker(MethodView):
    @auth_required()
    def get(self, worker_id: int = 0):
        return WorkerView.edit_view(object_id=worker_id)

    @auth_required()
    def put(self, worker_id):
        return WorkerView.update_view(object_id=worker_id)

    @auth_required()
    def delete(self, worker_id):
        return WorkerView.delete_view(object_id=worker_id)


class SourceGroupsAPI(MethodView):
    @auth_required()
    def get(self):
        return SourceGroupView.list_view()

    @auth_required()
    def post(self):
        return SourceGroupView.update_view(object_id="0")


class UpdateSourceGroup(MethodView):
    @auth_required()
    def get(self, osint_source_group_id: str = "0"):
        return SourceGroupView.edit_view(object_id=osint_source_group_id)

    @auth_required()
    def put(self, osint_source_group_id: str):
        return SourceGroupView.update_view(object_id=osint_source_group_id)

    @auth_required()
    def delete(self, osint_source_group_id: str):
        return SourceGroupView.delete_view(object_id=osint_source_group_id)


class BotsAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("bots/index.html")

    @auth_required()
    def post(self):
        return render_template("bots/index.html")


class UpdateBot(MethodView):
    @auth_required()
    def get(self, bot_id: int = 0):
        return render_template("bots/index.html")

    @auth_required()
    def put(self, bot_id):
        return render_template("bots/index.html")

    @auth_required()
    def delete(self, bot_id):
        return render_template("bots/index.html")


class ReportTypesAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("report_types/index.html")

    @auth_required()
    def post(self):
        return render_template("report_types/index.html")


class UpdateReportType(MethodView):
    @auth_required()
    def get(self, report_type_id: int = 0):
        return render_template("report_types/index.html")

    @auth_required()
    def put(self, report_type_id):
        return render_template("report_types/index.html")

    @auth_required()
    def delete(self, report_type_id):
        return render_template("report_types/index.html")


class AttributesAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("attributes/index.html")

    @auth_required()
    def post(self):
        return render_template("attributes/index.html")


class UpdateAttribute(MethodView):
    @auth_required()
    def get(self, attribute_id: int = 0):
        return render_template("attributes/index.html")

    @auth_required()
    def put(self, attribute_id):
        return render_template("attributes/index.html")

    @auth_required()
    def delete(self, attribute_id):
        return render_template("attributes/index.html")


class ProductTypesAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("product_types/index.html")

    @auth_required()
    def post(self):
        return render_template("product_types/index.html")


class UpdateProductType(MethodView):
    @auth_required()
    def get(self, product_type_id: int = 0):
        return render_template("product_types/index.html")

    @auth_required()
    def put(self, product_type_id):
        return render_template("product_types/index.html")

    @auth_required()
    def delete(self, product_type_id):
        return render_template("product_types/index.html")


class TemplatesAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("templates/index.html")

    @auth_required()
    def post(self):
        return render_template("templates/index.html")


class UpdateTemplate(MethodView):
    @auth_required()
    def get(self, template_id: int = 0):
        return render_template("templates/index.html")

    @auth_required()
    def put(self, template_id):
        return render_template("templates/index.html")

    @auth_required()
    def delete(self, template_id):
        return render_template("templates/index.html")


class PublishersAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("publishers/index.html")

    @auth_required()
    def post(self):
        return render_template("publishers/index.html")


class UpdatePublisher(MethodView):
    @auth_required()
    def get(self, publisher_id: int = 0):
        return render_template("publishers/index.html")

    @auth_required()
    def put(self, publisher_id):
        return render_template("publishers/index.html")

    @auth_required()
    def delete(self, publisher_id):
        return render_template("publishers/index.html")


class WordListsAPI(MethodView):
    @auth_required()
    def get(self):
        return WordListView.list_view()

    @auth_required()
    def post(self):
        return WordListView.update_view(object_id=0)


class UpdateWordList(MethodView):
    @auth_required()
    def get(self, word_list_id: int = 0):
        return WordListView.edit_view(object_id=word_list_id)

    @auth_required()
    def put(self, word_list_id):
        return WordListView.update_view(object_id=word_list_id)

    @auth_required()
    def delete(self, word_list_id):
        return WordListView.delete_view(object_id=word_list_id)


class WorkerTypesAPI(MethodView):
    @auth_required()
    def get(self):
        return render_template("worker_types/index.html")

    @auth_required()
    def post(self):
        return render_template("worker_types/index.html")


class UpdateWorkerType(MethodView):
    @auth_required()
    def get(self, worker_type_id: int = 0):
        return render_template("worker_types/index.html")

    @auth_required()
    def put(self, worker_type_id):
        return render_template("worker_types/index.html")

    @auth_required()
    def delete(self, worker_type_id):
        return render_template("worker_types/index.html")


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

    admin_bp.add_url_rule("/acls", view_func=ACLsAPI.as_view("acls"))
    admin_bp.add_url_rule("/acls/<int:acl_id>", view_func=UpdateACL.as_view("edit_acl"))

    admin_bp.add_url_rule("/workers", view_func=WorkersAPI.as_view("workers"))
    admin_bp.add_url_rule("/workers/<int:worker_id>", view_func=UpdateWorker.as_view("edit_worker"))

    admin_bp.add_url_rule("/worker_types", view_func=WorkerTypesAPI.as_view("worker_types"))
    admin_bp.add_url_rule("/worker_types/<int:worker_type_id>", view_func=UpdateWorkerType.as_view("edit_worker_type"))

    admin_bp.add_url_rule("/source_groups", view_func=SourceGroupsAPI.as_view("osint_source_groups"))
    admin_bp.add_url_rule("/source_groups/<string:osint_source_group_id>", view_func=UpdateSourceGroup.as_view("edit_osint_source_group"))

    admin_bp.add_url_rule("/bots", view_func=BotsAPI.as_view("bots"))
    admin_bp.add_url_rule("/bots/<int:bot_id>", view_func=UpdateBot.as_view("edit_bot"))

    admin_bp.add_url_rule("/report_types", view_func=ReportTypesAPI.as_view("report_types"))
    admin_bp.add_url_rule("/report_types/<int:report_type_id>", view_func=UpdateReportType.as_view("edit_report_type"))

    admin_bp.add_url_rule("/attributes", view_func=AttributesAPI.as_view("attributes"))
    admin_bp.add_url_rule("/attributes/<int:attribute_id>", view_func=UpdateAttribute.as_view("edit_attribute"))

    admin_bp.add_url_rule("/product_types", view_func=ProductTypesAPI.as_view("product_types"))
    admin_bp.add_url_rule("/product_types/<int:product_type_id>", view_func=UpdateProductType.as_view("edit_product_type"))

    admin_bp.add_url_rule("/templates", view_func=TemplatesAPI.as_view("templates"))
    admin_bp.add_url_rule("/templates/<int:template_id>", view_func=UpdateTemplate.as_view("edit_template"))

    admin_bp.add_url_rule("/publishers", view_func=PublishersAPI.as_view("publishers"))
    admin_bp.add_url_rule("/publishers/<int:publisher_id>", view_func=UpdatePublisher.as_view("edit_publisher"))

    admin_bp.add_url_rule("/word_lists", view_func=WordListsAPI.as_view("word_lists"))
    admin_bp.add_url_rule("/word_lists/<int:word_list_id>", view_func=UpdateWordList.as_view("edit_word_list"))

    app.register_blueprint(admin_bp)
