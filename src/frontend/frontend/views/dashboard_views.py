import json

import pandas as pd
import plotly.express as px
from flask import abort, render_template, request
from flask_jwt_extended import current_user
from models.dashboard import Cluster, Dashboard, NewsItemConflict, StoryConflict, TrendingCluster
from models.user import ProfileSettingsDashboard
from werkzeug.wrappers import Response

from frontend.auth import auth_required, update_current_user_cache
from frontend.cache import cache
from frontend.cache_models import CacheObject
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
        cluster = None
        try:
            page = parse_paging_data(request.args.to_dict(flat=False))

            logger.debug(f"Fetching Cluster {cluster_name} with: {page=}")

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
            base_route=cls.get_base_route(),
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
        if result is None:
            return render_template("errors/404.html", error="No story conflicts found"), 404
        conflict_list = []
        for conflict in result.get("conflicts", []):
            conflict_model = StoryConflict(**conflict)
            conflict_data = conflict_model.model_dump()
            conflict_data["existing_story"] = cls._deserialize_story_blob(conflict_model.existing_story)
            conflict_data["incoming_story"] = cls._deserialize_story_blob(conflict_model.incoming_story)
            conflict_list.append(conflict_data)
        logger.debug(f"Story conflict result: {result=}")
        template = "conflicts/_story_conflicts_list.html" if is_htmx_request() else "conflicts/story_conflicts.html"
        return render_template(template, story_conflicts=conflict_list)

    @classmethod
    @auth_required()
    def news_item_conflict_view(cls):
        try:
            grouped_conflicts, incoming_ids, duplicate_incoming_ids, remaining_stories = cls._build_news_item_conflict_view()
            template = "conflicts/_news_item_conflicts_list.html" if is_htmx_request() else "conflicts/news_item_conflicts.html"
            return render_template(
                template,
                grouped_conflicts=grouped_conflicts,
                incoming_ids=incoming_ids,
                duplicate_incoming_ids=duplicate_incoming_ids,
                remaining_stories=remaining_stories,
                template_marker="USING CORRECT FILE",
            )
        except Exception as error:
            logger.exception(f"Failed to render News Item Conflict View: {error}")
            return render_template("errors/404.html", error="No news item conflicts found"), 404

    @classmethod
    def _build_news_item_conflict_view(cls):
        persistence_layer = DataPersistenceLayer()

        conflict_cache_object = persistence_layer.get_objects(NewsItemConflict)
        conflict_records = conflict_cache_object.items
        internal_story_ids = {conflict.existing_story_id for conflict in conflict_records}

        internal_story_summaries = cls._load_internal_story_summaries(persistence_layer, internal_story_ids)

        grouped_conflicts = cls._group_conflicts_by_incoming_story(conflict_records)
        incoming_ids = cls._collect_incoming_news_item_ids(grouped_conflicts)
        cls._enrich_conflict_groups(grouped_conflicts, incoming_ids, internal_story_summaries)

        duplicate_incoming_ids = cls._find_duplicate_incoming_ids(grouped_conflicts)
        remaining_stories = [group_data["incoming_story"] for group_data in grouped_conflicts.values()]

        return grouped_conflicts, incoming_ids, duplicate_incoming_ids, remaining_stories

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
    def _group_conflicts_by_incoming_story(conflict_records: list[NewsItemConflict]) -> dict[str, dict]:
        grouped_conflicts: dict[str, dict] = {}
        for conflict in conflict_records:
            incoming_id = conflict.incoming_story_id

            if incoming_id not in grouped_conflicts:
                grouped_conflicts[incoming_id] = {
                    "incoming_story": conflict.incoming_story,
                    "conflict_entries": [],
                    "internal_stories": [],
                }

            grouped_conflicts[incoming_id]["conflict_entries"].append(conflict)
        return grouped_conflicts

    @staticmethod
    def _collect_incoming_news_item_ids(grouped_conflicts: dict[str, dict]) -> dict[str, set[str]]:
        incoming_ids: dict[str, set[str]] = {}
        for incoming_id, group_data in grouped_conflicts.items():
            incoming_story_items = group_data["incoming_story"].get("news_items", [])
            incoming_ids_set = {item["id"] for item in incoming_story_items if item.get("id")}
            incoming_ids[incoming_id] = incoming_ids_set
        return incoming_ids

    @classmethod
    def _enrich_conflict_groups(
        cls,
        grouped_conflicts: dict[str, dict],
        incoming_ids: dict[str, set[str]],
        internal_story_summaries: dict[str, dict],
    ) -> None:
        for incoming_id, group_data in grouped_conflicts.items():
            conflicts_by_story: dict[str, set[str]] = {}
            for entry in group_data["conflict_entries"]:
                conflicts_by_story.setdefault(entry.existing_story_id, set()).add(entry.news_item_id)

            incoming_story_items = group_data["incoming_story"].get("news_items", [])
            incoming_ids_set = incoming_ids[incoming_id]

            internal_ids_for_group = {c.existing_story_id for c in group_data["conflict_entries"]}
            enriched_internal_stories = []
            aggregated_existing_ids: set[str] = set()

            unique_source_items = group_data["conflict_entries"][0].unique_news_items if group_data["conflict_entries"] else []

            for story_id in internal_ids_for_group:
                summary = internal_story_summaries.get(story_id) or {}
                existing_news_item_ids = [item.get("id") for item in summary.get("news_item_data", []) if item.get("id")]
                aggregated_existing_ids.update(existing_news_item_ids)
                unique_ids = sorted(incoming_ids_set - conflicts_by_story.get(story_id, set()))
                unique_news_items = [item for item in unique_source_items if item.get("id") in unique_ids]
                enriched_internal_stories.append(
                    {
                        "story_id": story_id,
                        "summary": summary or None,
                        "existing_news_item_ids": existing_news_item_ids,
                        "unique_news_item_ids": unique_ids,
                        "unique_news_items": unique_news_items,
                    }
                )

            group_data["internal_stories"] = enriched_internal_stories
            conflict_unique_ids = sorted(incoming_ids_set - aggregated_existing_ids)
            incoming_story_map = {item.get("id"): item for item in incoming_story_items if item.get("id")}
            conflict_unique_items = [item for item in unique_source_items if item.get("id") in conflict_unique_ids]
            if len(conflict_unique_items) < len(conflict_unique_ids):
                conflict_unique_items = [incoming_story_map[item_id] for item_id in conflict_unique_ids if item_id in incoming_story_map]
            group_data["unique_news_item_ids"] = conflict_unique_ids
            group_data["unique_news_items"] = conflict_unique_items
            group_data["aggregated_existing_news_item_ids"] = sorted(aggregated_existing_ids)

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
    def _select_news_items(incoming_story: dict, allowed_ids: list[str] | None) -> list[dict]:
        news_items = incoming_story.get("news_items", [])
        if not allowed_ids:
            return news_items
        allowed_set = set(allowed_ids)
        return [item for item in news_items if item.get("id") in allowed_set]

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

    _list_payload_fields = {
        "existing_story_ids",
        "incoming_news_item_ids",
        "remaining_stories",
        "unique_incoming_news_item_ids",
        "resolved_conflict_item_ids",
        "existing_story_news_item_ids",
    }

    @classmethod
    def _extract_request_payload(cls) -> dict[str, object]:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload

        form_data = request.form.to_dict(flat=False)
        normalized: dict[str, object] = {}
        for key, values in form_data.items():
            if key in cls._list_payload_fields:
                normalized[key] = values
                continue
            if not isinstance(values, list):
                normalized[key] = values
            elif len(values) == 1:
                normalized[key] = values[0]
            else:
                normalized[key] = values
        return normalized

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

    @staticmethod
    def _load_internal_story_news_item_ids(story_id: str | None) -> list[str]:
        if not story_id:
            return []

        try:
            api = CoreApi()
            summary = api.api_get(f"/connectors/story-summary/{story_id}")
            if summary:
                return [item.get("id") for item in summary.get("news_item_data", []) if item.get("id")]
        except Exception as exc:
            logger.exception(f"Failed loading news items for internal story {story_id}: {exc}")
        return []

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

            # Normalize fields that must be lists
            def ensure_list(value):
                if value is None:
                    return []
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    if "," in value:
                        return [item.strip() for item in value.split(",") if item.strip()]
                    return [value]
                return [value]

            payload["incoming_story_id"] = payload.get("incoming_story_id") or payload.get("resolving_story_id")
            payload["remaining_stories"] = ensure_list(payload.get("remaining_stories"))

            supplied_news_items = payload.get("news_items")
            if isinstance(supplied_news_items, str):
                try:
                    supplied_news_items = json.loads(supplied_news_items)
                except json.JSONDecodeError:
                    supplied_news_items = None
            if supplied_news_items is not None and not isinstance(supplied_news_items, list):
                supplied_news_items = ensure_list(supplied_news_items)

            if supplied_news_items is None:
                payload["unique_incoming_news_item_ids"] = ensure_list(payload.get("unique_incoming_news_item_ids"))
                payload["resolved_conflict_item_ids"] = ensure_list(payload.get("resolved_conflict_item_ids"))
                payload["existing_story_news_item_ids"] = ensure_list(payload.get("existing_story_news_item_ids"))

            required_fields = [
                "incoming_story_id",
                "remaining_stories",
            ]

            missing = [f for f in required_fields if f not in payload]
            if missing:
                logger.error(f"Missing required fields: {missing}")
                return Response(f"Missing fields: {', '.join(missing)}", 400)

            incoming_story = cls._normalize_incoming_story(payload.get("incoming_story"))
            if not incoming_story:
                incoming_story = cls._load_incoming_story_snapshot(payload.get("incoming_story_id"))
            if not incoming_story:
                logger.error("Unable to load incoming story snapshot for POST payload")
                return Response("Unable to load incoming story data", 400)

            existing_ids_payload = payload.get("existing_story_news_item_ids")
            if isinstance(existing_ids_payload, str):
                try:
                    existing_ids_payload = json.loads(existing_ids_payload)
                except json.JSONDecodeError:
                    existing_ids_payload = ensure_list(existing_ids_payload)
            else:
                existing_ids_payload = ensure_list(existing_ids_payload)

            target_story_id = payload.get("story_id")
            if not existing_ids_payload and target_story_id:
                existing_ids_payload = cls._load_internal_story_news_item_ids(target_story_id)

            existing_ids = [str(item_id) for item_id in existing_ids_payload if item_id]

            if supplied_news_items is not None:
                unique_news_items = [item for item in supplied_news_items if isinstance(item, dict)]
            else:
                if not target_story_id:
                    logger.error("Missing story_id for legacy unique news ingestion flow")
                    return Response("Missing story_id for unique news ingestion", 400)
                allowed_items = cls._select_news_items(incoming_story, payload.get("unique_incoming_news_item_ids"))
                unique_news_items = allowed_items

            unique_news_items = [item for item in unique_news_items if item.get("id") not in existing_ids]
            unique_ids = [item.get("id") for item in unique_news_items if item.get("id")]

            if not unique_ids:
                logger.warning("No unique news items identified for ingestion")
                return Response("No unique news items to ingest", 400)

            payload["news_items"] = unique_news_items
            payload["resolved_conflict_item_ids"] = unique_ids
            payload.pop("existing_story_news_item_ids", None)
            payload.pop("unique_incoming_news_item_ids", None)
            payload.pop("story_id", None)
            payload.pop("incoming_story", None)
            payload.pop("incoming_story_id", None)

            api = CoreApi()
            response = api.api_post("/connectors/conflicts/news-items", json_data=payload)

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
