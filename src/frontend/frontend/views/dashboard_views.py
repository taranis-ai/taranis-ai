from flask import render_template, abort, request
from flask_jwt_extended import current_user

from models.dashboard import Dashboard, TrendingCluster
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView
from frontend.utils.form_data_parser import parse_formdata
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.config import Config
from frontend.auth import auth_required


class DashboardView(BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "dashboard/index.html"
    htmx_update_template = "dashboard/index.html"
    default_template = "dashboard/index.html"
    base_route = "base.dashboard"
    _is_admin = False
    _read_only = True
    _index = 10

    @classmethod
    def static_view(cls):
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
        except Exception:
            trending_clusters = []

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()
        context = {"data": dashboard[0], "clusters": trending_clusters, "error": error}
        return render_template(template, **context), 200

    @classmethod
    @auth_required()
    def get_cluster(cls, cluster_name: str):
        return render_template("dashboard/cluster.html", data=cluster_name), 200

    @classmethod
    @auth_required()
    def edit_dashboard(cls):
        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
        except Exception:
            trending_clusters = []

        user_profile = current_user.profile or {}
        dashboard_config = user_profile.get("dashboard", {})
        return render_template("dashboard/edit.html", dashboard=dashboard_config, clusters=trending_clusters)

    @classmethod
    @auth_required()
    def update_dashboard(cls):
        logger.debug(f"Updating {current_user} {request.form}")
        form_data = parse_formdata(request.form)

        if core_response := CoreApi().update_user_profile(form_data):
            response = cls.get_notification_from_response(core_response)
            table, table_response = cls.list_view()
            if table_response == 200:
                response += table
            return response, table_response

        return render_template("notification/index.html", notification={"message": "Failed to update dashboard settings", "error": True}), 400

    @classmethod
    def get_build_info(cls):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    def get(self, **kwargs):
        return self.static_view()

    def post(self):
        abort(405)

    def put(self, **kwargs):
        abort(405)

    def delete(self, **kwargs):
        abort(405)


class AdminDashboardView(BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "admin_dashboard/index.html"
    htmx_update_template = "admin_dashboard/index.html"
    default_template = "admin_dashboard/index.html"
    base_route = "admin.dashboard"
    _read_only = True
    _index = 10

    @classmethod
    def static_view(cls):
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()
        context = {"data": dashboard[0], "error": error, "build_info": cls.get_build_info()}
        return render_template(template, **context), 200

    @classmethod
    def get_build_info(cls):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    def get(self, **kwargs):
        return self.static_view()

    def post(self):
        abort(405)

    def put(self, **kwargs):
        abort(405)

    def delete(self, **kwargs):
        abort(405)
