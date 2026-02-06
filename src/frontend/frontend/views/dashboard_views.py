import pandas as pd
import plotly.express as px
from flask import abort, render_template, request, url_for
from flask_jwt_extended import current_user
from models.dashboard import Cluster, Dashboard, TrendingCluster
from models.user import ProfileSettingsDashboard
from werkzeug.wrappers import Response

from frontend.auth import auth_required, update_current_user_cache
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.router_helpers import parse_paging_data
from frontend.views.base_view import BaseView


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
    def static_view(cls):
        try:
            if dashboard_items := DataPersistenceLayer().get_objects(cls.model):
                dashboard = dashboard_items[0]
            else:
                return render_template("errors/404.html", error="No Dashboard items found"), 404
        except Exception as exc:
            logger.error(f"Error retrieving {cls.model_name()} items: {exc}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404

        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
            dashboard_config = current_user.profile.dashboard
        except Exception:
            trending_clusters = []
            dashboard_config = ProfileSettingsDashboard()

        return (
            render_template(
                "dashboard/index.html",
                data=dashboard,
                clusters=trending_clusters,
                dashboard_config=dashboard_config,
            ),
            200,
        )

    @classmethod
    @auth_required()
    def get_cluster(cls, cluster_name: str):
        try:
            paging = parse_paging_data(request.args.to_dict(flat=False))
            logger.debug(f"Fetching Cluster {cluster_name} with: {paging=}")

            cluster_endpoint = f"{Cluster._core_endpoint}/{cluster_name}"
            cluster = DataPersistenceLayer().get_objects_by_endpoint(Cluster, cluster_endpoint, paging)

        except ValueError:
            logger.exception(f"No cluster found for type: {cluster_name}")
            cluster = None
        except Exception:
            logger.exception(f"Error fetching cluster for type: {cluster_name}")
            cluster = None

        if not cluster:
            return render_template("errors/404.html", error="No cluster found"), 404

        if cluster_name in {"Country", "Location"}:
            country_data = [item.model_dump() for item in cluster]
            country_chart = cls.render_country_chart(country_data)
        else:
            country_chart = None

        columns = [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Size", "field": "size", "sortable": True, "renderer": None},
        ]

        return render_template(
            "dashboard/cluster.html",
            data=cluster,
            columns=columns,
            cluster_name=cluster_name,
            country_chart=country_chart,
            dashboard_config=current_user.profile.dashboard,
            base_route=url_for("base.cluster", cluster_name=cluster_name),
        ), 200

    @classmethod
    @auth_required()
    def edit_dashboard(cls):
        try:
            trending_clusters = CoreApi().api_get("/dashboard/cluster-names")
            if trending_clusters:
                trending_clusters = trending_clusters.get("items", [])
        except Exception:
            trending_clusters = []

        return render_template("dashboard/edit.html", dashboard=current_user.profile.dashboard, clusters=trending_clusters)

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

    def post(self, *args, **kwargs) -> Response:
        form_data = parse_formdata(request.form)
        form_data = {"dashboard": form_data.get("dashboard", {})}
        core_response = CoreApi().update_user_profile(form_data)
        update_current_user_cache()
        DataPersistenceLayer().invalidate_cache_by_object(TrendingCluster)

        if not core_response:
            html = render_template(
                "notification/index.html",
                notification={"message": "Failed to update dashboard settings", "error": True},
            )
            return Response(html, status=400)

        notification_html = self.get_notification_from_response(core_response)

        if core_response.ok:
            self.add_flash_notification(core_response)
            return Response(
                status=204,
                headers={"HX-Redirect": url_for("base.dashboard")},
            )

        return Response(notification_html, status=core_response.status_code or 400)

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)
