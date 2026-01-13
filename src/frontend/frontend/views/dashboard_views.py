from typing import Any

import pandas as pd
import plotly.express as px
from flask import abort, render_template, request, url_for
from flask_jwt_extended import current_user
from models.dashboard import Cluster, Dashboard, TrendingCluster
from models.user import ProfileSettingsDashboard
from werkzeug.wrappers import Response

from frontend.auth import auth_required, update_current_user_cache
from frontend.cache_models import CacheObject
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
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
            user_dashboard = current_user.profile.dashboard
        except Exception:
            trending_clusters = []
            user_dashboard = ProfileSettingsDashboard()

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()

        context = {"data": dashboard[0], "clusters": trending_clusters, "error": error, "dashboard_config": user_dashboard}
        return render_template(template, **context), 200

    @classmethod
    @auth_required()
    def get_cluster(cls, cluster_name: str):
        cluster: CacheObject[Any] | None = None

        try:
            paging = parse_paging_data(request.args.to_dict(flat=False))
            logger.debug(f"Fetching Cluster {cluster_name} with: {paging=}")

            core_params: dict[str, Any] = dict(paging.query_params or {})
            page_number = paging.page or 1
            raw_limit = core_params.pop("limit", None)
            try:
                per_page = int(raw_limit) if raw_limit is not None else (paging.limit or 50)
            except (TypeError, ValueError):
                per_page = paging.limit or 50

            order = paging.order or "size_desc"

            core_params["page"] = page_number
            core_params["per_page"] = per_page
            core_params["order"] = order

            cluster_endpoint = f"{Cluster._core_endpoint}/{cluster_name}"
            result = DataPersistenceLayer().api.api_get(cluster_endpoint, core_params)

            if not result:
                raise ValueError("Empty cluster response")

            items = [Cluster(**item) for item in result.get("items", [])]
            total_count = result.get("total_count", len(items))

            cluster = CacheObject(
                items,
                total_count=total_count,
                limit=per_page,
                page=page_number,
                order=order,
                query_params=core_params,
                links=result.get("_links", {}),
            )

        except Exception as exc:
            logger.exception(f"Error retrieving cluster {cluster_name}: {exc}")
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

        return (
            render_template(
                "dashboard/cluster.html",
                data=cluster,
                columns=columns,
                cluster_name=cluster_name,
                country_chart=country_chart,
                dashboard_config=current_user.profile.dashboard,
                base_route=url_for("base.cluster", cluster_name=cluster_name),
            ),
            200,
        )

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

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        form_data = parse_formdata(request.form)
        form_data = {"dashboard": form_data.get("dashboard", {})}

        if core_response := CoreApi().update_user_profile(form_data):
            response = self.get_notification_from_response(core_response)
        else:
            response = render_template(
                "notification/index.html", notification={"message": "Failed to update dashboard settings", "error": True}
            )

        update_current_user_cache()
        DataPersistenceLayer().invalidate_cache_by_object(TrendingCluster)
        dashboard, table_response = self.static_view()
        if table_response == 200:
            response += dashboard
        return response, table_response

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)
