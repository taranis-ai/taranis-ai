import json

import pandas as pd
import plotly.express as px
from flask import abort, render_template, request, url_for
from flask_jwt_extended import current_user
from models.dashboard import Cluster, Dashboard, NewsItemConflict, StoryConflict, TrendingCluster
from models.user import ProfileSettingsDashboard
from werkzeug.wrappers import Response

from frontend.auth import auth_required, update_current_user_cache
from frontend.cache import cache
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
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
    @auth_required()
    def conflict_menu(cls):
        return render_template("conflicts/conflict_menu.html")

    @classmethod
    @auth_required()
    def story_conflict_view(cls):
        result = CoreApi().get_story_conflicts()
        if result is not None:
            conflict_list = [cls._build_story_conflict_payload(conflict) for conflict in result.get("conflicts", [])]
            template = "conflicts/_story_conflicts_list.html" if is_htmx_request() else "conflicts/story_conflicts.html"
            return render_template(template, story_conflicts=conflict_list)

    @classmethod
    @auth_required()
    def news_item_conflict_view(cls):
        try:
            persistence_layer = DataPersistenceLayer()
            conflict_cache_object = persistence_layer.get_objects(NewsItemConflict)
            conflicts = conflict_cache_object.items
            internal_story_ids = {conflict.existing_story_id for conflict in conflicts}

            story_summaries = cls._load_internal_story_summaries(persistence_layer, internal_story_ids)
            grouped_conflicts = cls._group_conflicts_by_incoming_story(conflicts)
            incoming_ids = cls._collect_incoming_news_item_ids(grouped_conflicts)
            cls._annotate_conflict_groups(grouped_conflicts, incoming_ids, story_summaries)
            duplicate_incoming_ids = cls._find_duplicate_incoming_ids(grouped_conflicts)
            remaining_stories = [group_data["incoming_story"] for group_data in grouped_conflicts.values()]
            template = "conflicts/_news_item_conflicts_list.html" if is_htmx_request() else "conflicts/news_item_conflicts.html"
            return render_template(
                template,
                grouped_conflicts=grouped_conflicts,
                incoming_ids=incoming_ids,
                duplicate_incoming_ids=duplicate_incoming_ids,
                remaining_stories=remaining_stories,
                story_summaries=story_summaries,
            )
        except Exception as error:
            logger.exception(f"Failed to render News Item Conflict View: {error}")
            return render_template("errors/404.html", error="No news item conflicts found"), 404

    @staticmethod
    def _load_internal_story_summaries(persistence_layer: DataPersistenceLayer, story_ids: set[str]) -> dict[str, dict]:
        internal_story_summaries: dict[str, dict] = {}
        for story_id in story_ids:
            summary_endpoint = f"/connectors/story-summary/{story_id}"
            summary_cache_key = persistence_layer.make_user_key(summary_endpoint)

            if cached_summary := cache.get(summary_cache_key):
                internal_story_summaries[story_id] = cached_summary
                continue

            if summary_response := persistence_layer.api.api_get(summary_endpoint):
                internal_story_summaries[story_id] = summary_response
                cache.set(summary_cache_key, summary_response)
        return internal_story_summaries

    @staticmethod
    def _group_conflicts_by_incoming_story(conflicts: list[NewsItemConflict]) -> dict[str, dict]:
        grouped_conflicts: dict[str, dict] = {}
        for conflict in conflicts:
            incoming_story_id = conflict.incoming_story_id

            if incoming_story_id not in grouped_conflicts:
                grouped_conflicts[incoming_story_id] = {
                    "incoming_story": conflict.incoming_story,
                    "conflicts": [],
                }

            grouped_conflicts[incoming_story_id]["conflicts"].append(conflict)
        return grouped_conflicts

    @staticmethod
    def _collect_incoming_news_item_ids(grouped_conflicts: dict[str, dict]) -> dict[str, list[str]]:
        incoming_story_ids: dict[str, list[str]] = {}
        for incoming_story_id, group_data in grouped_conflicts.items():
            incoming_story_items = group_data["incoming_story"].get("news_items", [])
            incoming_story_ids_list = sorted({item["id"] for item in incoming_story_items if item.get("id")})
            incoming_story_ids[incoming_story_id] = incoming_story_ids_list
        return incoming_story_ids

    @classmethod
    def _annotate_conflict_groups(
        cls,
        grouped_conflicts: dict[str, dict],
        incoming_ids: dict[str, list[str]],
        story_summaries: dict[str, dict],
    ) -> None:
        for incoming_story_id, group_data in grouped_conflicts.items():
            conflicts = group_data["conflicts"]
            incoming_story = group_data["incoming_story"]

            internal_story_ids = list({conflict.existing_story_id for conflict in conflicts})
            group_data["internal_story_ids"] = internal_story_ids
            group_data["has_internal"] = bool(internal_story_ids)

            aggregated_existing_ids: list[str] = []
            seen_ids = set()
            for story_id in internal_story_ids:
                summary = story_summaries.get(story_id) or {}
                for item in summary.get("news_item_data", []) or []:
                    item_id = item.get("id")
                    if item_id and item_id not in seen_ids:
                        aggregated_existing_ids.append(item_id)
                        seen_ids.add(item_id)

            group_data["aggregated_existing_news_item_ids"] = aggregated_existing_ids

            incoming_story_ids = incoming_ids.get(incoming_story_id, [])
            unique_news_item_ids = [item_id for item_id in incoming_story_ids if item_id not in seen_ids]
            group_data["unique_news_item_ids"] = unique_news_item_ids

            incoming_items = incoming_story.get("news_items", []) or []
            unique_id_set = set(unique_news_item_ids)
            unique_items = [item for item in incoming_items if item.get("id") in unique_id_set]
            group_data["unique_news_items"] = unique_items

    @staticmethod
    def _find_duplicate_incoming_ids(grouped_conflicts: dict[str, dict]) -> set[str]:
        news_item_occurrences: dict[str, int] = {}
        for group_data in grouped_conflicts.values():
            for item in group_data["incoming_story"].get("news_items", []):
                if item["id"] not in news_item_occurrences:
                    news_item_occurrences[item["id"]] = 0
                news_item_occurrences[item["id"]] += 1
        return {item_id for item_id, count in news_item_occurrences.items() if count > 1}

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
    def _deserialize_story_blob(data: str | dict | None) -> dict:
        """
        Convert stored JSON strings into dictionaries for template/HTMX usage.
        """
        if isinstance(data, dict):
            return data
        if not data:
            return {}
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error("Unable to decode story blob for conflict payload")
        return {}

    @classmethod
    def _build_story_conflict_payload(cls, conflict: dict) -> dict:
        conflict_model = StoryConflict(**conflict)
        conflict_data = conflict_model.model_dump()
        conflict_data["existing_story"] = cls._deserialize_story_blob(conflict_model.existing_story)
        conflict_data["incoming_story"] = cls._deserialize_story_blob(conflict_model.incoming_story)
        return conflict_data

    @classmethod
    def _extract_request_payload(cls) -> dict[str, object]:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
        return parse_formdata(request.form)

    @staticmethod
    def _safe_json_load(value: str | None) -> object | None:
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload fragment for news conflict request")
        return None

    @staticmethod
    def _normalize_incoming_story(raw_value: object) -> dict | None:
        if isinstance(raw_value, str):
            raw_value = raw_value.strip()
            if not raw_value:
                return None
            try:
                raw_value = json.loads(raw_value)
            except json.JSONDecodeError:
                logger.error("incoming_story payload is not valid JSON")
                return None

        return raw_value if isinstance(raw_value, dict) else None

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
            logger.error(f"Story conflict resolve failed for {story_id}: {resp.status_code} {resp.text}")
            refresh = CoreApi().get_story_conflicts() or {}
            conflict_list = [StoryConflict(**c) for c in refresh.get("conflicts", [])]
            if is_htmx_request():
                html = render_template("conflicts/_story_conflicts_list.html", story_conflicts=conflict_list)
                return Response(html, 200)
            return Response(f"Error resolving conflict: {resp.text}", resp.status_code)

        result = api.get_story_conflicts()
        conflict_list = [StoryConflict(**c) for c in result.get("conflicts", [])]
        template = "conflicts/_story_conflicts_list.html" if is_htmx_request() else "conflicts/story_conflicts.html"
        return render_template(template, story_conflicts=conflict_list)

    @classmethod
    @auth_required("ASSESS_UPDATE")
    def resolve_news_item_conflict_post(cls):
        """
        Keep local story but ingest unique items.
        Accepts JSON or standard form submissions.
        """
        try:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                payload = parse_formdata(request.form)
            if not isinstance(payload, dict):
                return Response("Invalid payload", 400)

            incoming_story_id = payload.get("incoming_story_id")
            if not incoming_story_id:
                return Response("Missing incoming_story_id", 400)

            raw_news_items = payload.get("news_items")
            if isinstance(raw_news_items, str):
                raw_news_items = cls._safe_json_load(raw_news_items)
            if not isinstance(raw_news_items, list):
                return Response("Missing news_items", 400)

            existing_ids_raw = payload.get("existing_story_news_item_ids") or []
            if not isinstance(existing_ids_raw, list):
                existing_ids_raw = [existing_ids_raw] if existing_ids_raw else []
            existing_set = {str(item_id) for item_id in existing_ids_raw if item_id}

            deduped_items: list[dict] = []
            seen_lookup: set[str] = set()
            unique_ids: list[str] = []
            for item in raw_news_items:
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id")
                if not item_id or item_id in existing_set or item_id in seen_lookup:
                    continue
                seen_lookup.add(item_id)
                deduped_items.append(item)
                unique_ids.append(item_id)

            if not deduped_items:
                logger.warning("No unique news items identified for ingestion")
                return Response("No unique news items to ingest", 400)

            remaining_raw = payload.get("remaining_stories") or []
            remaining_stories = remaining_raw if isinstance(remaining_raw, list) else ([remaining_raw] if remaining_raw else [])

            api_payload = {
                "incoming_story_id": incoming_story_id,
                "remaining_stories": remaining_stories,
                "news_items": deduped_items,
                "resolved_conflict_item_ids": unique_ids,
            }

            response = CoreApi().api_post("/connectors/conflicts/news-items", json_data=api_payload)

            if not response.ok:
                logger.error(f"Core API error: {response.status_code} {response.text}")
                return Response(response.text, response.status_code)

            return cls.news_item_conflict_view()

        except Exception as exc:
            logger.exception(f"Failed POST add-unique-items: {exc}")
            return Response("Internal error adding unique news items", 500)

    @classmethod
    @auth_required("ASSESS_UPDATE")
    def resolve_news_item_conflict_put(cls):
        try:
            payload = cls._extract_request_payload()

            incoming_story = cls._normalize_incoming_story(payload.get("incoming_story"))
            if not incoming_story:
                incoming_story = cls._load_incoming_story_snapshot(payload.get("incoming_story_id"))
            if not incoming_story:
                logger.error("Unable to resolve conflict without incoming story data")
                return Response("Unable to load incoming story data", 400)

            payload["incoming_story"] = incoming_story

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
