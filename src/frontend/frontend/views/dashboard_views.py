from flask import json, render_template, abort, request
from flask_jwt_extended import current_user
import plotly.express as px
import pandas as pd
from werkzeug.wrappers import Response


from models.dashboard import Dashboard, TrendingCluster, Cluster, StoryConflict, NewsItemConflict
from models.user import ProfileSettingsDashboard
from frontend.cache_models import CacheObject, PagingData
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView
from frontend.utils.form_data_parser import parse_formdata
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
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
        try:
            persistence_layer = DataPersistenceLayer()

            conflict_cache_object = persistence_layer.get_objects(NewsItemConflict)
            conflict_records = conflict_cache_object.items

            logger.debug(f"Loaded {len(conflict_records)} news item conflicts.")
            logger.debug(f"Conflict records: {[conflict.model_dump() for conflict in conflict_records]}")

            internal_story_ids = {conflict.existing_story_id for conflict in conflict_records}

            internal_story_summaries = {}

            for story_id in internal_story_ids:
                summary_endpoint = f"/connectors/story-summary/{story_id}"
                summary_cache_key = persistence_layer.make_user_key(summary_endpoint)

                if cached_summary := cache.get(summary_cache_key):
                    internal_story_summaries[story_id] = cached_summary
                    continue

                if summary_response := persistence_layer.api.api_get(summary_endpoint):
                    internal_story_summaries[story_id] = summary_response
                    cache.set(summary_cache_key, summary_response)

            grouped_conflicts = {}

            for conflict in conflict_records:
                incoming_id = conflict.incoming_story_id

                if incoming_id not in grouped_conflicts:
                    grouped_conflicts[incoming_id] = {
                        "incoming_story": conflict.incoming_story,
                        "conflict_entries": [],
                        "internal_stories": [],
                    }

                grouped_conflicts[incoming_id]["conflict_entries"].append(conflict)

            for group_data in grouped_conflicts.values():
                internal_ids_for_group = {c.existing_story_id for c in group_data["conflict_entries"]}

                group_data["internal_stories"] = [
                    {"story_id": story_id, "summary": internal_story_summaries.get(story_id)} for story_id in internal_ids_for_group
                ]
            incoming_ids = {
                incoming_id: {item["id"] for item in group_data["incoming_story"]["news_items"]}
                for incoming_id, group_data in grouped_conflicts.items()
            }

            news_item_occurrences = {}

            for group_data in grouped_conflicts.values():
                for item in group_data["incoming_story"]["news_items"]:
                    if item["id"] not in news_item_occurrences:
                        news_item_occurrences[item["id"]] = 0
                    news_item_occurrences[item["id"]] += 1

            duplicate_incoming_ids = {item_id for item_id, count in news_item_occurrences.items() if count > 1}
            remaining_stories = [group_data["incoming_story"] for group_data in grouped_conflicts.values()]

            return render_template(
                "conflicts/news_item_conflicts.html",
                grouped_conflicts=grouped_conflicts,
                incoming_ids=incoming_ids,
                duplicate_incoming_ids=duplicate_incoming_ids,
                remaining_stories=remaining_stories,
                template_marker="USING CORRECT FILE",
            )
            # return render_template("conflicts/news_item_conflicts.html", template_marker="USING CORRECT FILE")
        except Exception as error:
            logger.exception(f"Failed to render News Item Conflict View: {error}")
            return render_template("errors/404.html", error="No news item conflicts found"), 404

    @staticmethod
    def _load_incoming_story_snapshot(incoming_story_id: str | None) -> dict | None:
        if not incoming_story_id:
            return None

        try:
            persistence_layer = DataPersistenceLayer()
            conflict_cache_object = persistence_layer.get_objects(NewsItemConflict)
            for conflict in conflict_cache_object.items:
                if conflict.incoming_story_id == incoming_story_id:
                    return conflict.incoming_story
        except Exception as exc:
            logger.exception(f"Failed loading incoming story snapshot for {incoming_story_id}: {exc}")
        return None

    @staticmethod
    def _select_news_items(incoming_story: dict, allowed_ids: list[str] | None) -> list[dict]:
        news_items = incoming_story.get("news_items", [])
        if not allowed_ids:
            return news_items
        allowed_set = set(allowed_ids)
        return [item for item in news_items if item.get("id") in allowed_set]

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
    @auth_required("ASSESS_UPDATE")
    def resolve_news_item_conflict_post(cls):
        """
        Keep local story but ingest unique items.
        Accepts both JSON and form-encoded HTMX data.
        Includes full debugging output.
        """
        try:
            logger.warning("========== DEBUG: NEWS CONFLICT POST ==========")
            logger.warning(f"Content-Type: {request.content_type}")
            logger.warning(f"RAW request.data: {request.data}")
            logger.warning(f"RAW request.get_data(): {request.get_data()}")
            logger.warning(f"request.json: {request.json}")
            logger.warning(f"request.form: {request.form}")
            logger.warning("================================================")

            # Try JSON first
            payload = request.get_json(silent=True)
            logger.warning(f"DEBUG: payload from get_json(): {payload} ({type(payload)})")

            # Fall back to form
            if not payload:
                logger.warning("DEBUG: Falling back to form data")
                form = request.form.to_dict(flat=False)
                logger.warning(f"DEBUG: Raw form dict: {form}")

                payload = {k: (v[0] if len(v) == 1 else v) for k, v in form.items()}

            logger.warning(f"DEBUG BEFORE NORMALIZATION: {payload}")

            # Normalize fields that must be lists
            def ensure_list(v):
                if v is None:
                    return []
                if isinstance(v, list):
                    return v
                if isinstance(v, str):
                    if "," in v:
                        return [x.strip() for x in v.split(",") if x.strip()]
                    return [v]
                return [v]

            payload["incoming_story_id"] = payload.get("incoming_story_id") or payload.get("resolving_story_id")
            payload["news_items"] = ensure_list(payload.get("news_items"))
            payload["resolved_conflict_item_ids"] = ensure_list(payload.get("resolved_conflict_item_ids"))
            payload["remaining_stories"] = ensure_list(payload.get("remaining_stories"))

            logger.warning(f"DEBUG AFTER NORMALIZATION: {payload}")

            # Required fields
            required_fields = [
                "story_id",
                "news_items",
                "resolved_conflict_item_ids",
                "remaining_stories",
            ]

            missing = [f for f in required_fields if f not in payload]
            if missing:
                logger.error(f"Missing required fields: {missing}")
                return Response(f"Missing fields: {', '.join(missing)}", 400)

            incoming_story = cls._load_incoming_story_snapshot(payload.get("incoming_story_id"))
            if not incoming_story:
                logger.error("Unable to load incoming story snapshot for POST payload")
                return Response("Unable to load incoming story data", 400)

            payload["news_items"] = cls._select_news_items(incoming_story, payload.get("resolved_conflict_item_ids"))
            payload.pop("incoming_story_id", None)

            # Forward to core API
            logger.warning(f"DEBUG: Sending payload to Core API: {payload}")
            api = CoreApi()
            response = api.api_post("/connectors/conflicts/news-items", json_data=payload)

            if not response.ok:
                logger.error(f"Core API error: {response.status_code} {response.text}")
                return Response(response.text, response.status_code)

            logger.warning("DEBUG: Core API returned OK, reloading conflict view")
            return cls.news_item_conflict_view()

        except Exception as exc:
            logger.exception(f"Failed POST add-unique-items: {exc}")
            return Response("Internal error adding unique news items", 500)

    @classmethod
    @auth_required("ASSESS_UPDATE")
    def resolve_news_item_conflict_put(cls):
        """
        Accept JSON or HTMX form-encoded data.
        """
        try:
            payload = request.get_json(silent=True)

            if not payload:
                form = request.form.to_dict(flat=False)
                payload = {key: (value[0] if len(value) == 1 else value) for key, value in form.items()}

            payload["incoming_story_id"] = payload.get("incoming_story_id") or payload.get("resolving_story_id")

            required_fields = [
                "resolving_story_id",
                "incoming_story_id",
                "existing_story_ids",
                "incoming_news_item_ids",
                "remaining_stories",
            ]

            if missing := [f for f in required_fields if f not in payload]:
                return Response(f"Missing fields: {', '.join(missing)}", 400)

            if not payload.get("incoming_story"):
                incoming_story = cls._load_incoming_story_snapshot(payload.get("incoming_story_id"))
                if not incoming_story:
                    logger.error("Unable to load incoming story snapshot for PUT payload")
                    return Response("Unable to load incoming story data", 400)
                payload["incoming_story"] = incoming_story

            payload.pop("incoming_story_id", None)

            api = CoreApi()
            response = api.api_put("/connectors/conflicts/news-items", json_data=payload)

            if not response.ok:
                return Response(response.text, response.status_code)

            return cls.news_item_conflict_view()

        except Exception as exc:
            logger.exception(f"Failed PUT news-item conflict resolve: {exc}")
            return Response("Internal error resolving conflict", 500)

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
