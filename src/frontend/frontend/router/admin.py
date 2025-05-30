from flask import Flask, render_template, Blueprint, request
from flask.views import MethodView
from models.admin import Job

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache_models import PagingData
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required
from frontend.router_helpers import convert_query_params
from frontend.views import (
    UserView,
    OrganizationView,
    RoleView,
    WorkerView,
    BotView,
    ProductTypeView,
    WordListView,
    SourceGroupView,
    SourceView,
    ReportItemTypeView,
    AttributeView,
    TemplateView,
    PublisherView,
    ACLView,
    ConnectorView,
    SchedulerView,
    DashboardView,
)


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


class ACLItemAPI(MethodView):
    @auth_required()
    def get(self):
        item_type = request.args.get("item_type", "")
        return ACLView.get_acl_item_ids_view(item_type)


class OSINTSourceParameterAPI(MethodView):
    @auth_required()
    def get(self, osint_source_id: str):
        collector_type = request.args.get("collector_type", "")
        return SourceView.get_osint_source_parameters_view(osint_source_id, collector_type)


def init(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/admin")

    admin_bp.add_url_rule("/", view_func=DashboardView.as_view("dashboard"))

    admin_bp.add_url_rule("/attributes", view_func=AttributeView.as_view("attributes"))
    admin_bp.add_url_rule("/attributes/<int:attribute_id>", view_func=AttributeView.as_view("edit_attribute"))

    admin_bp.add_url_rule("/users", view_func=UserView.as_view("users"))
    admin_bp.add_url_rule("/users/<int:user_id>", view_func=UserView.as_view("edit_user"))
    admin_bp.add_url_rule("/export/users", view_func=ExportUsers.as_view("export_users"))
    admin_bp.add_url_rule("/import/users", view_func=ImportUsers.as_view("import_users"))

    admin_bp.add_url_rule("/scheduler", view_func=SchedulerView.as_view("scheduler"))
    admin_bp.add_url_rule("/scheduler/job/<string:job_id>", view_func=SchedulerView.as_view("edit_job"))

    admin_bp.add_url_rule("/organizations", view_func=OrganizationView.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/<int:organization_id>", view_func=OrganizationView.as_view("edit_organization"))

    admin_bp.add_url_rule("/roles", view_func=RoleView.as_view("roles"))
    admin_bp.add_url_rule("/roles/<int:role_id>", view_func=RoleView.as_view("edit_role"))

    admin_bp.add_url_rule("/acls", view_func=ACLView.as_view("acls"))
    admin_bp.add_url_rule("/acls/<int:acl_id>", view_func=ACLView.as_view("edit_acl"))
    admin_bp.add_url_rule("/acl/item_ids", view_func=ACLItemAPI.as_view("acl_item_ids"))

    admin_bp.add_url_rule("/connectors", view_func=ConnectorView.as_view("connectors"))
    admin_bp.add_url_rule("/connectors/<string:connector_id>", view_func=ConnectorView.as_view("edit_connector"))

    admin_bp.add_url_rule("/workers", view_func=WorkerView.as_view("worker_types"))
    admin_bp.add_url_rule("/workers/<int:worker_type_id>", view_func=WorkerView.as_view("edit_worker_type"))

    admin_bp.add_url_rule("/source_groups", view_func=SourceGroupView.as_view("osint_source_groups"))
    admin_bp.add_url_rule("/source_groups/<string:osint_source_group_id>", view_func=SourceGroupView.as_view("edit_osint_source_group"))

    admin_bp.add_url_rule("/sources", view_func=SourceView.as_view("osint_sources"))
    admin_bp.add_url_rule("/sources/<string:osint_source_id>", view_func=SourceView.as_view("edit_osint_source"))
    admin_bp.add_url_rule("/source_parameters/<string:osint_source_id>", view_func=OSINTSourceParameterAPI.as_view("osint_source_parameters"))

    admin_bp.add_url_rule("/bots", view_func=BotView.as_view("bots"))
    admin_bp.add_url_rule("/bots/<int:bot_id>", view_func=BotView.as_view("edit_bot"))

    admin_bp.add_url_rule("/report_types", view_func=ReportItemTypeView.as_view("report_item_types"))
    admin_bp.add_url_rule("/report_types/<int:report_item_type_id>", view_func=ReportItemTypeView.as_view("edit_report_item_type"))

    admin_bp.add_url_rule("/product_types", view_func=ProductTypeView.as_view("product_types"))
    admin_bp.add_url_rule("/product_types/<int:product_type_id>", view_func=ProductTypeView.as_view("edit_product_type"))

    admin_bp.add_url_rule("/templates", view_func=TemplateView.as_view("template_data"))
    admin_bp.add_url_rule("/templates/<string:template>", view_func=TemplateView.as_view("edit_template"))

    admin_bp.add_url_rule("/publisher", view_func=PublisherView.as_view("publisher_presets"))
    admin_bp.add_url_rule("/publishers/<int:publisher_preset_id>", view_func=PublisherView.as_view("edit_publisher_preset"))

    admin_bp.add_url_rule("/word_lists", view_func=WordListView.as_view("word_lists"))
    admin_bp.add_url_rule("/word_lists/<int:word_list_id>", view_func=WordListView.as_view("edit_word_list"))

    app.register_blueprint(admin_bp)
