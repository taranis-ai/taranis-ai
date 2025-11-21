from flask import json, render_template, abort, request
from flask_jwt_extended import current_user
import plotly.express as px
import pandas as pd
from werkzeug.wrappers import Response


from models.dashboard import Dashboard, TrendingCluster, Cluster, StoryConflict
from models.user import ProfileSettingsDashboard
from frontend.cache_models import CacheObject, PagingData
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView
from frontend.utils.form_data_parser import parse_formdata
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.config import Config
from frontend.auth import auth_required, update_current_user_cache
from frontend.cache import cache
from frontend.utils.router_helpers import convert_query_params


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

        if cluster_filter := user_dashboard.trending_cluster_filter:
            trending_clusters = [cluster for cluster in trending_clusters if cluster.name in cluster_filter]

        context = {"data": dashboard[0], "clusters": trending_clusters, "error": error, "dashboard_config": user_dashboard}
        return render_template(template, **context), 200

    @classmethod
    @auth_required()
    def get_cluster(cls, cluster_name: str):
        cluster = None
        try:
            params = convert_query_params(request.args, PagingData)
            page = PagingData(**params)

            logger.debug(f"Fetching Cluster {cluster_name} with params: {params}")

            dpl = DataPersistenceLayer()
            endpoint = f"{Cluster._core_endpoint}/{cluster_name}"
            cache_object: CacheObject | None
            if cache_object := cache.get(key=dpl.make_user_key(endpoint)):
                cluster = cache_object.search_and_paginate(page)
            elif result := dpl.api.api_get(endpoint):
                cluster = dpl._cache_and_paginate_objects(result, Cluster, endpoint, page)
        except Exception:
            cluster = None

        if not cluster:
            logger.error(f"Error retrieving {cluster_name}")
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
        ), 200

    @classmethod
    @auth_required()
    def edit_dashboard(cls):
        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
        except Exception:
            trending_clusters = []

        return render_template("dashboard/edit.html", dashboard=current_user.profile.dashboard, clusters=trending_clusters)

    @classmethod
    @auth_required()
    def conflict_menu(cls):
        return render_template("conflicts/conflict_menu.html")

    @classmethod
    @auth_required()
    def story_conflict_view(cls):
        result = CoreApi().get_story_conflicts()
        if result is None:
            return render_template("errors/404.html", error="No story conflicts found"), 404
        conflict_list = []
        conflict_list.extend(StoryConflict(**conflict) for conflict in result.get("conflicts", []))
        logger.debug(f"Story conflict result: {result=}")
        return render_template("conflicts/story_conflicts.html", story_conflicts=conflict_list)

    @classmethod
    @auth_required()
    def news_item_conflict_view(cls):
        return render_template("conflicts/news_item_conflicts.html")

    @classmethod
    @auth_required("ASSESS_UPDATE")
    def resolve_story_conflict(cls, story_id: str):
        resolved = request.form.get("resolved_story")
        incoming_original = request.form.get("incoming_original")

        if not resolved:
            return Response("Missing resolved_story", 400)

        try:
            resolved_json = json.loads(resolved)
        except Exception:
            return Response("Invalid JSON in resolved_story", 400)

        try:
            incoming_json = json.loads(incoming_original) if incoming_original else {}
        except Exception:
            incoming_json = {}

        api = CoreApi()
        resp = api.resolve_story_conflict(
            story_id=story_id,
            resolution=resolved_json,
            incoming_story_original=incoming_json,
        )

        if not resp.ok:
            return Response(f"Error resolving conflict: {resp.text}", resp.status_code)

        result = api.get_story_conflicts()
        conflict_list = [StoryConflict(**c) for c in result.get("conflicts", [])]

        return render_template("conflicts/story_conflicts.html", story_conflicts=conflict_list)

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
        logger.debug(f"Updating dashboard with data: {form_data}")

        if core_response := CoreApi().update_user_profile(form_data):
            response = self.get_notification_from_response(core_response)
        else:
            response = render_template(
                "notification/index.html", notification={"message": "Failed to update dashboard settings", "error": True}
            )

        update_current_user_cache()
        dashboard, table_response = self.static_view()
        if table_response == 200:
            response += dashboard
        return response, table_response

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)
