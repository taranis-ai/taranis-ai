from flask import render_template, abort, request
from flask_jwt_extended import current_user
import plotly.express as px
import pandas as pd
from typing import Any

from models.dashboard import Dashboard, TrendingCluster
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView
from frontend.utils.form_data_parser import parse_formdata
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.config import Config
from frontend.auth import auth_required, update_current_user_cache


class DashboardView(BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "dashboard/index.html"
    htmx_update_template = "dashboard/index.html"
    default_template = "dashboard/index.html"
    base_route = "base.dashboard"
    _is_admin = False
    _read_only = True

    @classmethod
    def static_view(cls, dashboard_config: dict | None = None):
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        user_dashboard: dict[str, Any] = {}

        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
            if dashboard_config is None:
                user_dashboard = current_user.profile.get("dashboard", {})
            else:
                user_dashboard = dashboard_config
        except Exception:
            trending_clusters = []
            user_dashboard = {}

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()

        if cluster_filter := user_dashboard.get("trending_cluster_filter"):
            trending_clusters = [cluster for cluster in trending_clusters if cluster.name in cluster_filter]

        context = {"data": dashboard[0], "clusters": trending_clusters, "error": error, "dashboard_config": dashboard_config}
        return render_template(template, **context), 200

    @classmethod
    @auth_required()
    def get_cluster(cls, cluster_name: str):
        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
        except Exception:
            trending_clusters = []

        cluster = [c for c in trending_clusters if c.name == cluster_name]
        user_profile = current_user.profile or {}
        dashboard_config = user_profile.get("dashboard", {})

        if not cluster:
            logger.error(f"Error retrieving {cluster_name}")
            return render_template("errors/404.html", error="No cluster found"), 404

        if cluster_name == "Country":
            country_data = cluster[0].model_dump().get("tags", [])
            logger.debug(f"Country data for cluster '{cluster_name}': {country_data}")
            country_chart = cls.render_country_chart(country_data)
        else:
            country_chart = None

        return render_template("dashboard/cluster.html", data=cluster[0], country_chart=country_chart, dashboard_config=dashboard_config), 200

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
    def get_build_info(cls):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    @classmethod
    def render_country_chart(cls, country_data: list[dict]) -> str:
        df = pd.DataFrame(country_data)

        fig = px.scatter_geo(df, locations="name", locationmode="country names", size="size", hover_name="name", projection="natural earth")
        fig.update_traces(marker=dict(sizemode="area", sizemin=4))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))

        # Return only the div/JS part so it can be used in Jinja directly
        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    def get(self, **kwargs) -> tuple[str, int]:
        return self.static_view()

    def post(self, *args, **kwargs) -> tuple[str, int]:
        form_data = parse_formdata(request.form)
        form_data = {"dashboard": form_data.get("dashboard", {})}
        logger.debug(f"Updating dashboard with data: {form_data}")

        if core_response := CoreApi().update_user_profile(form_data):
            response = self.get_notification_from_response(core_response)
        else:
            response = render_template(
                "notification/index.html", notification={"message": "Failed to update dashboard settings", "error": True}
            )

        dashboard_config = None
        if updated_user := update_current_user_cache():
            if user_profile := updated_user.profile:
                dashboard_config = user_profile.get("dashboard", {})
        dashboard, table_response = self.static_view(dashboard_config)
        if table_response == 200:
            response += dashboard
        return response, table_response

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
    def pretty_name(cls) -> str:
        return "Admin Dashboard"

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
        context = {"data": dashboard[0], "error": error, "build_info": cls.get_build_info(), "_is_admin": cls._is_admin}
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
