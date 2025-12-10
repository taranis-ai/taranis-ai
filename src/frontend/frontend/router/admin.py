from flask import Blueprint, Flask, request
from flask.views import MethodView

from frontend.auth import auth_required
from frontend.views import (
    ACLView,
    AdminDashboardView,
    AttributeView,
    BotView,
    ConnectorView,
    OrganizationView,
    ProductTypeView,
    PublisherView,
    ReportItemTypeView,
    RoleView,
    SourceGroupView,
    SourceView,
    TemplateView,
    UserView,
    WordListView,
    WorkerView,
)

from frontend.views.admin_views.scheduler_views import (
    ScheduleActiveJobsAPI,
    ScheduleFailedJobsAPI,
    ScheduleHistoryAPI,
    ScheduleJobsAPI,
    ScheduleQueuesAPI,
    ScheduleRetryJobAPI,
    SchedulerView,
)


class ImportUsers(MethodView):
    @auth_required()
    def get(self):
        return UserView.import_view()

    @auth_required()
    def post(self):
        return UserView.import_post_view()


class ExportOSINTSources(MethodView):
    @auth_required()
    def get(self):
        return SourceView.export_view()


class ImportOSINTSources(MethodView):
    @auth_required()
    def get(self):
        return SourceView.import_view()

    @auth_required()
    def post(self):
        return SourceView.import_post_view()


class LoadDefaultOSINTSources(MethodView):
    @auth_required()
    def post(self):
        return SourceView.load_default_osint_sources()


class OSINTSourceCollect(MethodView):
    @auth_required()
    def post(self, osint_source_id: str | None = None):
        if osint_source_id:
            return SourceView.collect_osint_source(osint_source_id)
        return SourceView.collect_all_osint_sources()


class ImportWordLists(MethodView):
    @auth_required()
    def get(self):
        return WordListView.import_view()

    @auth_required()
    def post(self):
        return WordListView.import_post_view()


class ACLItemAPI(MethodView):
    @auth_required()
    def get(self):
        item_type = request.args.get("item_type", "")
        return ACLView.get_acl_item_ids_view(item_type)


class OSINTSourceParameterAPI(MethodView):
    @auth_required()
    def get(self, osint_source_id: str):
        collector_type = request.args.get("type", "")
        return SourceView.get_osint_source_parameters_view(osint_source_id, collector_type)


class PublisherParameterAPI(MethodView):
    @auth_required()
    def get(self, publisher_id: str):
        publisher_type = request.args.get("type", "")
        return PublisherView.get_publisher_parameters_view(publisher_id, publisher_type)


class ProductTypeParameterAPI(MethodView):
    @auth_required()
    def get(self, product_type_id: int) -> str:
        presenter_type = request.args.get("type", "")
        return ProductTypeView.get_product_type_parameters_view(product_type_id, presenter_type)


class ReportItemTypeGroupsAPI(MethodView):
    @auth_required()
    def post(self):
        group_index = request.form.get("group_index", type=int) or 0
        return ReportItemTypeView.get_report_item_type_groups_view(group_index)


class ReportItemTypeGroupItemAPI(MethodView):
    @auth_required()
    def post(self):
        group_index = request.form.get("attribute_group_index", type=int) or 0
        attribute_index = request.form.get("attribute_index", type=int) or 0
        return ReportItemTypeView.get_report_item_type_group_items_view(group_index, attribute_index)


class ConnectorParameterAPI(MethodView):
    @auth_required()
    def get(self, connector_id: str):
        connector_type = request.args.get("type", "")
        return ConnectorView.get_connector_parameters_view(connector_id, connector_type)


def init(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/admin")

    admin_bp.add_url_rule("/", view_func=AdminDashboardView.as_view("dashboard"))

    admin_bp.add_url_rule("/attributes", view_func=AttributeView.as_view("attributes"))
    admin_bp.add_url_rule("/attributes/<int:attribute_id>", view_func=AttributeView.as_view("edit_attribute"))

    admin_bp.add_url_rule("/users", view_func=UserView.as_view("users"))
    admin_bp.add_url_rule("/users/<int:user_id>", view_func=UserView.as_view("edit_user"))
    admin_bp.add_url_rule("/export/users", view_func=UserView.export_view, methods=["GET"], endpoint="export_users")
    admin_bp.add_url_rule("/import/users", view_func=ImportUsers.as_view("import_users"))

    admin_bp.add_url_rule("/scheduler", view_func=SchedulerView.as_view("scheduler"))
    admin_bp.add_url_rule("/scheduler/job/<string:job_id>", view_func=SchedulerView.as_view("edit_job"))
    admin_bp.add_url_rule("/scheduler/jobs", view_func=ScheduleJobsAPI.as_view("scheduler_jobs_table"))
    admin_bp.add_url_rule("/scheduler/queues", view_func=ScheduleQueuesAPI.as_view("scheduler_queue_cards"))
    admin_bp.add_url_rule("/scheduler/active", view_func=ScheduleActiveJobsAPI.as_view("scheduler_active_jobs"))
    admin_bp.add_url_rule("/scheduler/failed", view_func=ScheduleFailedJobsAPI.as_view("scheduler_failed_jobs"))
    admin_bp.add_url_rule("/scheduler/history", view_func=ScheduleHistoryAPI.as_view("scheduler_history"))
    admin_bp.add_url_rule("/scheduler/retry/<string:job_id>", view_func=ScheduleRetryJobAPI.as_view("scheduler_retry_job"))

    admin_bp.add_url_rule("/organizations", view_func=OrganizationView.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/<int:organization_id>", view_func=OrganizationView.as_view("edit_organization"))

    admin_bp.add_url_rule("/roles", view_func=RoleView.as_view("roles"))
    admin_bp.add_url_rule("/roles/<int:role_id>", view_func=RoleView.as_view("edit_role"))

    admin_bp.add_url_rule("/acls", view_func=ACLView.as_view("acls"))
    admin_bp.add_url_rule("/acls/<int:acl_id>", view_func=ACLView.as_view("edit_acl"))
    admin_bp.add_url_rule("/acl/item_ids", view_func=ACLItemAPI.as_view("acl_item_ids"))

    admin_bp.add_url_rule("/connectors", view_func=ConnectorView.as_view("connectors"))
    admin_bp.add_url_rule("/connectors/<string:connector_id>", view_func=ConnectorView.as_view("edit_connector"))
    admin_bp.add_url_rule("/connector_parameters/<string:connector_id>", view_func=ConnectorParameterAPI.as_view("connector_parameters"))

    admin_bp.add_url_rule("/workers", view_func=WorkerView.as_view("worker_types"))
    admin_bp.add_url_rule("/workers/<string:worker_type_id>", view_func=WorkerView.as_view("edit_worker_type"))

    admin_bp.add_url_rule("/source_groups", view_func=SourceGroupView.as_view("osint_source_groups"))
    admin_bp.add_url_rule("/source_groups/<string:osint_source_group_id>", view_func=SourceGroupView.as_view("edit_osint_source_group"))

    admin_bp.add_url_rule("/sources", view_func=SourceView.as_view("osint_sources"))
    admin_bp.add_url_rule("/sources/<string:osint_source_id>", view_func=SourceView.as_view("edit_osint_source"))
    admin_bp.add_url_rule("/source_parameters/<string:osint_source_id>", view_func=OSINTSourceParameterAPI.as_view("osint_source_parameters"))
    admin_bp.add_url_rule(
        "/toggle_source_state/<string:osint_source_id>/<string:new_state>", view_func=SourceView.toggle_osint_source_state, methods=["POST"]
    )
    admin_bp.add_url_rule("/export/osint_sources", view_func=ExportOSINTSources.as_view("export_osint_sources"))
    admin_bp.add_url_rule("/import/osint_sources", view_func=ImportOSINTSources.as_view("import_osint_sources"))
    admin_bp.add_url_rule("/load_default_osint_sources", view_func=LoadDefaultOSINTSources.as_view("load_default_osint_sources"))
    admin_bp.add_url_rule(
        "/source_preview/<string:osint_source_id>",
        view_func=SourceView.get_osint_source_preview_view,
        methods=["GET"],
        endpoint="osint_source_preview",
    )
    admin_bp.add_url_rule("/source_collect", view_func=OSINTSourceCollect.as_view("collect_osint_source_all"))
    admin_bp.add_url_rule("/source_collect/<string:osint_source_id>", view_func=OSINTSourceCollect.as_view("collect_osint_source"))

    admin_bp.add_url_rule("/bots", view_func=BotView.as_view("bots"))
    admin_bp.add_url_rule("/bots/<string:bot_id>", view_func=BotView.as_view("edit_bot"))
    admin_bp.add_url_rule(
        "/bot_parameters/<string:bot_id>", view_func=BotView.get_bot_parameters_view, methods=["GET"], endpoint="bot_parameters"
    )
    admin_bp.add_url_rule("/bot_execute/<string:bot_id>", view_func=BotView.execute_bot, methods=["POST"])

    admin_bp.add_url_rule("/report_types", view_func=ReportItemTypeView.as_view("report_item_types"))
    admin_bp.add_url_rule("/report_types/<int:report_item_type_id>", view_func=ReportItemTypeView.as_view("edit_report_item_type"))
    admin_bp.add_url_rule("/add_report_type_group", view_func=ReportItemTypeGroupsAPI.as_view("add_report_item_types_group"))
    admin_bp.add_url_rule("/add_report_type_group_item", view_func=ReportItemTypeGroupItemAPI.as_view("add_report_item_types_group_item"))

    admin_bp.add_url_rule("/product_types", view_func=ProductTypeView.as_view("product_types"))
    admin_bp.add_url_rule("/product_types/<int:product_type_id>", view_func=ProductTypeView.as_view("edit_product_type"))
    admin_bp.add_url_rule(
        "/product_type_parameters/<int:product_type_id>", view_func=ProductTypeParameterAPI.as_view("product_type_parameters")
    )

    admin_bp.add_url_rule("/templates", view_func=TemplateView.as_view("template_data"))
    admin_bp.add_url_rule("/templates/<string:template>", view_func=TemplateView.as_view("edit_template"))

    admin_bp.add_url_rule("/publisher", view_func=PublisherView.as_view("publisher_presets"))
    admin_bp.add_url_rule("/publisher/<string:publisher_preset_id>", view_func=PublisherView.as_view("edit_publisher_preset"))
    admin_bp.add_url_rule("/publisher_parameters/<string:publisher_id>", view_func=PublisherParameterAPI.as_view("publisher_parameters"))

    admin_bp.add_url_rule("/word_lists", view_func=WordListView.as_view("word_lists"))
    admin_bp.add_url_rule("/word_lists/<int:word_list_id>", view_func=WordListView.as_view("edit_word_list"))
    admin_bp.add_url_rule("/export/word_lists", view_func=WordListView.export_view, methods=["GET"], endpoint="export_word_lists")
    admin_bp.add_url_rule("/import/word_lists", view_func=ImportWordLists.as_view("import_word_lists"))
    admin_bp.add_url_rule("/update-word_lists", view_func=WordListView.update_word_lists, methods=["POST"], endpoint="update_all_word_lists")
    admin_bp.add_url_rule(
        "/load_default_word_lists", view_func=WordListView.load_default_word_lists, methods=["POST"], endpoint="load_default_word_lists"
    )

    app.register_blueprint(admin_bp)
