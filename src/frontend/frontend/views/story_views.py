import datetime
import uuid
from json import JSONDecodeError
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urlencode, urlparse

from flask import Response, abort, flash, json, make_response, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from flask_jwt_extended import current_user
from models.assess import (
    NEWS_ITEM_IMPORT_FIELDS,
    STORY_IMPORT_FIELDS,
    AssessSource,
    BulkAction,
    Connector,
    FilterLists,
    NewsItem,
    Story,
    StoryUpdatePayload,
)
from models.report import ReportItem
from models.revision_diff import build_story_revision_diff_payload
from pydantic import ValidationError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required, update_current_user_cache
from frontend.cache import add_model_to_cache, get_model_from_cache
from frontend.cache_models import CacheObject, PagingData
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.views.base_view import BaseView


def _sanitize_news_item_import_payload(news_item_data: dict[str, Any], story_id: str | None = None) -> dict[str, Any]:
    sanitized_payload = {key: value for key, value in news_item_data.items() if key in NEWS_ITEM_IMPORT_FIELDS}
    if story_id:
        sanitized_payload["story_id"] = story_id
    return sanitized_payload


def _sanitize_story_import_payload(story_data: dict[str, Any]) -> dict[str, Any]:
    sanitized_payload = {key: value for key, value in story_data.items() if key in STORY_IMPORT_FIELDS}
    if news_items := story_data.get("news_items"):
        sanitized_payload["news_items"] = [
            _sanitize_news_item_import_payload(news_item_data, sanitized_payload.get("id")) for news_item_data in news_items
        ]
    return sanitized_payload


def _normalize_story_import_payload(json_data: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
    if isinstance(json_data, dict) and isinstance(json_data.get("items"), list):
        json_data = json_data["items"]
    if isinstance(json_data, list) and all(isinstance(story_data, dict) for story_data in json_data):
        return [_sanitize_story_import_payload(story_data) for story_data in json_data]
    if isinstance(json_data, dict):
        return _sanitize_story_import_payload(json_data)
    return json_data


ASSESS_FILTER_KEYS = frozenset(
    {
        "search",
        "source",
        "group",
        "tags",
        "language",
        "read",
        "important",
        "in_report",
        "relevant",
        "cybersecurity",
        "changed_by",
        "range",
        "sort",
        "timefrom",
        "timeto",
    }
)
ASSESS_FILTER_MULTI_KEYS = frozenset({"source", "group", "tags", "language"})
ASSESS_SAVED_FILTER_SESSION_KEY = "assess_saved_filter_active"
ASSESS_SAVED_FILTER_NAME_MAX_LENGTH = 80


class StoryView(BaseView):
    model = Story
    icon = "newspaper"
    htmx_list_template = "assess/story_table.html"
    htmx_update_template = "assess/story.html"
    edit_template = "assess/story_edit.html"
    default_template = "assess/index.html"

    base_route = "assess.assess"
    edit_route = "assess.story_edit"
    _show_sidebar = True

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        filter_lists = cls.get_filter_lists()
        base_context["filter_lists"] = filter_lists
        assess_request_args: dict[str, list[str]] = {}
        if request.endpoint == "assess.assess":
            assess_request_args = cls._get_assess_request_params()
            base_context["assess_request_args"] = assess_request_args
        base_context["source_filter_select"] = cls._build_source_filter_select(filter_lists, assess_request_args)
        base_context["language_filter_select"] = cls._build_language_filter_select(filter_lists, assess_request_args)
        if stories := base_context.get("stories"):
            enhanced_stories = cls._get_enhanced_stories(stories, list(base_context["filter_lists"].sources))
            base_context["story_ids"] = [story.id for story in enhanced_stories if getattr(story, "id", None)]
            base_context["stories"] = enhanced_stories
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        return "stories"

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "assess/sidebar/sidebar.html"

    @staticmethod
    def _get_enhanced_stories(stories: CacheObject[Story], sources: list[AssessSource]) -> CacheObject[Story]:
        source_dict = {source.id: source for source in sources if source.id}
        return CacheObject(
            [StoryView._enhance_story_with_details(story, source_dict) for story in stories.items],
            total_count=stories.total_count,
        )

    @staticmethod
    def _enhance_story_with_details(story: Story, sources: dict[str, Any]) -> Story:
        if not story.news_items:
            return story
        if first_news_item := story.news_items[0]:
            if source := sources.get(first_news_item.osint_source_id):
                # Add the source as an pydantic extra field to the story for easier access in the template
                story.source_info = source  # type: ignore
            story.summary_content = story.summary or first_news_item.content  # type: ignore
        return story

    @staticmethod
    def get_filter_lists() -> FilterLists:
        username = getattr(current_user, "username", getattr(current_user, "id", "anonymous"))
        if filter_lists := get_model_from_cache(FilterLists._model_name, "", username):
            return FilterLists(**filter_lists)
        if filter_lists_content := CoreApi().get_filter_lists():
            filter_lists = FilterLists(**filter_lists_content)
            add_model_to_cache(filter_lists, "", username)
            return filter_lists
        return FilterLists(tags=[], sources=[], groups=[])

    @staticmethod
    def _filter_token_item(value: str, label: str, name: str, group: str | None = None) -> dict[str, str]:
        item = {"value": value, "label": label, "name": name}
        if group:
            item["group"] = group
        return item

    @staticmethod
    def _get_group_field(group: Any, field: str) -> str:
        value = group.get(field) if isinstance(group, dict) else getattr(group, field, None)
        return str(value) if value not in (None, "") else ""

    @classmethod
    def _build_source_filter_select(cls, filter_lists: FilterLists, request_args: dict[str, list[str]]) -> dict[str, list[dict[str, str]]]:
        selected_sources = request_args.get("source", [])
        selected_groups = request_args.get("group", [])
        selected_source_ids = set(selected_sources)
        selected_group_ids = set(selected_groups)
        source_ids: set[str] = set()
        group_ids: set[str] = set()
        options: list[dict[str, str]] = []
        selected_items: list[dict[str, str]] = []

        for source in filter_lists.sources:
            source_id = str(source.id) if source.id else ""
            if not source_id:
                continue
            source_ids.add(source_id)
            option = cls._filter_token_item(source_id, source.name, "source", "Source")
            options.append(option)
            if source_id in selected_source_ids:
                selected_items.append(option)

        for group in filter_lists.groups:
            group_id = cls._get_group_field(group, "id")
            if not group_id:
                continue
            group_ids.add(group_id)
            group_name = cls._get_group_field(group, "name") or group_id
            option = cls._filter_token_item(group_id, group_name, "group", "Group")
            options.append(option)
            if group_id in selected_group_ids:
                selected_items.append(option)

        selected_items.extend(
            cls._filter_token_item(source_id, source_id, "source", "Source") for source_id in selected_sources if source_id not in source_ids
        )
        selected_items.extend(
            cls._filter_token_item(group_id, group_id, "group", "Group") for group_id in selected_groups if group_id not in group_ids
        )

        return {"options": options, "selected_items": selected_items}

    @classmethod
    def _build_language_filter_select(cls, filter_lists: FilterLists, request_args: dict[str, list[str]]) -> dict[str, list[dict[str, str]]]:
        selected_languages = request_args.get("language", [])
        available_languages = [str(language) for language in (filter_lists.languages or []) if language not in (None, "")]
        available_language_ids = set(available_languages)
        selected_language_ids = set(selected_languages)
        options: list[dict[str, str]] = []
        selected_items: list[dict[str, str]] = []

        for language in available_languages:
            option = cls._filter_token_item(language, language.upper(), "language")
            options.append(option)
            if language in selected_language_ids:
                selected_items.append(option)

        selected_items.extend(
            cls._filter_token_item(language, language.upper(), "language")
            for language in selected_languages
            if language not in available_language_ids
        )

        return {"options": options, "selected_items": selected_items}

    @staticmethod
    def _normalize_assess_filter_values(values: Any) -> list[str]:
        if values in (None, ""):
            return []
        if isinstance(values, (list, tuple, set)):
            return [str(value) for value in values if value not in (None, "")]
        return [str(values)]

    @classmethod
    def _normalize_assess_filter_payload(cls, filters: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, values in filters.items():
            if key not in ASSESS_FILTER_KEYS:
                continue
            normalized_values = cls._normalize_assess_filter_values(values)
            if not normalized_values:
                continue
            if key in ASSESS_FILTER_MULTI_KEYS:
                normalized[key] = normalized_values
            else:
                normalized[key] = normalized_values[0]
        return normalized

    @classmethod
    def _filter_payload_to_request_params(cls, filters: dict[str, Any]) -> dict[str, list[str]]:
        params: dict[str, list[str]] = {}
        for key, value in cls._normalize_assess_filter_payload(filters).items():
            values = [str(item) for item in value if item not in (None, "")] if isinstance(value, list) else [str(value)]
            if values:
                params[key] = values
        return params

    @classmethod
    def _get_saved_assess_filters(cls) -> list[dict[str, Any]]:
        profile = getattr(current_user, "profile", None)
        raw_filters = getattr(profile, "assess_saved_filters", None) if profile is not None else None
        if not isinstance(raw_filters, list):
            return []

        saved_filters: list[dict[str, Any]] = []
        default_seen = False
        for raw_filter in raw_filters:
            if not hasattr(raw_filter, "model_dump"):
                continue
            saved_filter = raw_filter.model_dump(mode="json")

            filter_id = str(saved_filter.get("id") or "").strip()
            name = str(saved_filter.get("name") or "").strip()
            filters = saved_filter.get("filters")
            if not filter_id or not name or not isinstance(filters, dict):
                continue
            normalized_filters = cls._normalize_assess_filter_payload(filters)
            if not normalized_filters:
                continue
            is_default = bool(saved_filter.get("is_default")) and not default_seen
            default_seen = default_seen or is_default
            saved_filters.append({"id": filter_id, "name": name, "filters": normalized_filters, "is_default": is_default})
        return saved_filters

    @classmethod
    def _get_default_assess_saved_filter_params(cls) -> dict[str, list[str]]:
        default_filter = next((saved_filter for saved_filter in cls._get_saved_assess_filters() if saved_filter["is_default"]), None)
        if not default_filter:
            return {}
        return cls._filter_payload_to_request_params(default_filter["filters"])

    @classmethod
    def _get_saved_filters_dialog_context(cls, saved_filters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        saved_filters = saved_filters if saved_filters is not None else cls._get_saved_assess_filters()
        return {
            "saved_filters": cls.get_saved_filter_links(saved_filters),
            "has_current_filters": bool(cls._extract_assess_filters_from_request()),
            "assess_saved_filter_name_max_length": ASSESS_SAVED_FILTER_NAME_MAX_LENGTH,
        }

    @classmethod
    def get_saved_filter_links(cls, saved_filters: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        saved_filters = saved_filters if saved_filters is not None else cls._get_saved_assess_filters()
        return [
            {
                **saved_filter,
                "url": cls._build_assess_filters_url(cls._filter_payload_to_request_params(saved_filter["filters"])),
            }
            for saved_filter in saved_filters
        ]

    @classmethod
    def _get_assess_request_params(cls, request_params: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
        params = {
            key: [value for value in values if value not in (None, "")]
            for key, values in (request_params or request.args.to_dict(flat=False)).items()
        }
        has_reset = "reset" in params
        params.pop("reset", None)
        if has_reset:
            session.pop(ASSESS_SAVED_FILTER_SESSION_KEY, None)
            return {}

        if not params:
            saved_defaults = cls._get_default_assess_saved_filter_params()
            if saved_defaults and not is_htmx_request():
                session[ASSESS_SAVED_FILTER_SESSION_KEY] = True
                return {key: values[:] for key, values in saved_defaults.items()}

            if request.method == "GET" and is_htmx_request():
                session.pop(ASSESS_SAVED_FILTER_SESSION_KEY, None)
            elif request.method == "POST" and session.get(ASSESS_SAVED_FILTER_SESSION_KEY) and saved_defaults:
                return {key: values[:] for key, values in saved_defaults.items()}
            return {}

        if request.method == "GET" and is_htmx_request() and not set(params).intersection(ASSESS_FILTER_KEYS):
            session.pop(ASSESS_SAVED_FILTER_SESSION_KEY, None)
            return params

        return params

    @classmethod
    def _extract_assess_filters_from_request(cls) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        request_values = request.form if request.method != "GET" else request.args
        for key in ASSESS_FILTER_MULTI_KEYS:
            values = [value for value in request_values.getlist(key) if value not in (None, "")]
            if values:
                filters[key] = values
        for key in ASSESS_FILTER_KEYS - ASSESS_FILTER_MULTI_KEYS:
            value = request_values.get(key, "")
            if value not in ("", None):
                filters[key] = value
        return cls._normalize_assess_filter_payload(filters)

    @classmethod
    def _build_assess_filters_url(cls, request_params: dict[str, list[str]]) -> str:
        query_string = urlencode(request_params, doseq=True)
        base_url = cls.get_base_route()
        return f"{base_url}?{query_string}" if query_string else base_url

    @classmethod
    def _build_assess_selection_key(cls, request_params: dict[str, list[str]]) -> str:
        selection_params = {key: values[:] for key, values in sorted(request_params.items()) if key not in {"offset", "page"} and values}
        return urlencode(selection_params, doseq=True)

    @classmethod
    def default_share_story_link(cls) -> str:
        return f"mailto:?{urlencode({'subject': 'sharing stories from taranis ai'}, quote_via=quote)}"

    @classmethod
    @auth_required()
    def get_sharing_dialog(cls) -> str:
        story_ids = request.args.getlist("story_ids")
        if not story_ids and (story_id := request.args.get("story_id", "")):
            story_ids = [story_id]

        connectors = []
        mail_sharing_link = cls.default_share_story_link()
        try:
            mail_sharing_link = cls.share_story_link(story_ids)
            connectors = DataPersistenceLayer().get_objects(Connector)
        except HTTPException as exc:
            logger.warning(f"Failed to enrich share dialog: {exc}")
        except Exception as exc:
            logger.warning(f"Failed to enrich share dialog: {exc}")
        finally:
            return render_template(
                "assess/story_sharing_dialog.html",
                connectors=connectors,
                story_ids=story_ids,
                mail_sharing_link=mail_sharing_link,
            )

    @classmethod
    @auth_required()
    def submit_sharing_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return make_response(cls.render_response_notification({"error": "No stories selected for sharing."}), 400)

        logger.debug(f"Submitting sharing dialog for story {story_ids} - {request.form}")
        connector_id = request.form.get("connector", "")
        if not connector_id:
            return make_response(cls.render_response_notification({"error": "No connector selected for sharing."}), 400)

        try:
            core_response = CoreApi().api_post(f"/assess/story/{connector_id}/share", json_data={"story_ids": story_ids})
            notification_html = cls.get_notification_from_response(core_response)
            status_code = getattr(core_response, "status_code", 500) or 500
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to share stories with connector.")
            notification_html = cls.render_response_notification({"error": "Failed to share stories with connector."})
            status_code = 500

        return make_response(notification_html, status_code)

    @classmethod
    def share_story_link(cls, story_ids: list[str]) -> str:
        stories: list[Story] = []
        for story_id in story_ids:
            try:
                story = DataPersistenceLayer().get_object(Story, story_id)
            except HTTPException as exc:
                logger.warning(f"Failed to load story {story_id} for sharing link: {exc}")
                continue
            except Exception as exc:
                logger.warning(f"Failed to load story {story_id} for sharing link: {exc}")
                continue
            if story is not None:
                stories.append(story)

        subject = "sharing stories from taranis ai"
        if len(stories) == 1:
            subject = stories[0].title or subject

        body_lines: list[str] = []
        for story in stories:
            title = story.title or f"Story {story.id}"
            if story.links is not None:
                links = [f" - {link}\n" for link in story.links]
                body_lines.append(f"{title}:\n{''.join(links)}")
        body = "\n\n".join(body_lines).strip()

        params: dict[str, str] = {"subject": subject}
        if body:
            params["body"] = body

        return f"mailto:?{urlencode(params, quote_via=quote)}"

    @classmethod
    @auth_required()
    def get_report_dialog(cls) -> tuple[str, int]:
        story_ids = request.args.getlist("story_ids")
        logger.debug(f"Opening report dialog for stories {story_ids}")
        reports = DataPersistenceLayer().get_objects(ReportItem)
        target = "#assess"
        if StoryView._get_current_url_path() != url_for("assess.assess"):
            target = f"#story-{story_ids[0]}"

        return render_template("assess/story_report_dialog.html", story_ids=story_ids, reports=reports, target=target), 200

    @classmethod
    @auth_required()
    def submit_report_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        report_id = request.form.get("report", "")
        response = CoreApi().api_post(f"/analyze/report-items/{report_id}/stories", json_data=story_ids)
        notification_html = cls.get_notification_from_response(response)
        if StoryView._get_current_url_path() == url_for("assess.assess"):
            return cls.rerender_list(notification=notification_html)
        else:
            content = cls._get_action_response_content(story_ids[0])
            return make_response(notification_html + content, 200)

    @classmethod
    @auth_required()
    def get_cluster_dialog(cls) -> tuple[str, int]:
        story_ids = request.args.getlist("story_ids")
        logger.debug(f"Opening cluster dialog for stories {story_ids}")
        stories = [DataPersistenceLayer().get_object(Story, s) for s in story_ids]
        return render_template("assess/story_grouping_dialog.html", stories=stories), 200

    @classmethod
    @auth_required()
    def submit_cluster_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        open_primary_story = request.form.get("open_primary") == "true"
        if len(story_ids) < 2:
            return cls.rerender_list(
                notification=cls.render_response_notification({"error": "At least two stories must be selected for clustering."})
            )
        logger.debug(f"Clustering {story_ids[1:]} into {story_ids[0]}")
        response = CoreApi().api_post("/assess/stories/group", json_data=story_ids)
        notification_html = cls.get_notification_from_response(response)

        if open_primary_story and getattr(response, "ok", False):
            primary_story_id = story_ids[0]
            cls.add_flash_notification(response)
            return cls.redirect_htmx(url_for("assess.story", story_id=primary_story_id))

        return cls.rerender_list(notification=notification_html)

    @classmethod
    @auth_required()
    def get_search_dialog(cls) -> tuple[str, int]:
        current_search = request.args.get("search", "")
        return render_template("assess/sidebar/search_dialog.html", current_search=current_search), 200

    @classmethod
    @auth_required()
    def get_saved_filters_dialog(cls) -> tuple[str, int]:
        return cls._render_saved_filters_dialog()

    @classmethod
    def _render_saved_filters_dialog(
        cls,
        notification: dict[str, Any] | None = None,
        status: int = 200,
        saved_filters: list[dict[str, Any]] | None = None,
    ) -> tuple[str, int]:
        context = cls._get_saved_filters_dialog_context(saved_filters)
        if notification:
            context["notification"] = notification
        return render_template("assess/sidebar/saved_filters_dialog.html", **context), status

    @classmethod
    def _saved_filters_profile_payload(cls, saved_filters: list[dict[str, Any]]) -> dict[str, Any]:
        default_seen = False
        normalized_filters = []
        for saved_filter in saved_filters:
            filters = saved_filter.get("filters")
            if not isinstance(filters, dict):
                continue
            normalized = cls._normalize_assess_filter_payload(filters)
            if not normalized:
                continue
            is_default = bool(saved_filter.get("is_default")) and not default_seen
            default_seen = default_seen or is_default
            normalized_filters.append(
                {
                    "id": str(saved_filter.get("id") or uuid.uuid7()),
                    "name": str(saved_filter.get("name") or "").strip(),
                    "filters": normalized,
                    "is_default": is_default,
                }
            )
        return {"assess_saved_filters": [saved_filter for saved_filter in normalized_filters if saved_filter["name"]]}

    @classmethod
    def _update_saved_filters_profile(cls, saved_filters: list[dict[str, Any]]):
        response = CoreApi().update_user_profile(cls._saved_filters_profile_payload(saved_filters))
        if getattr(response, "ok", False):
            update_current_user_cache()
        return response

    @classmethod
    def _render_saved_filters_mutation_response(cls, response, success_message: str, saved_filters: list[dict[str, Any]]):
        if getattr(response, "ok", False):
            return cls._render_saved_filters_dialog({"message": success_message}, saved_filters=saved_filters)

        payload = None
        try:
            if response and response.content:
                payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            notification = cls.get_notification_from_dict(payload)
        else:
            notification = {"message": "No response from core API", "error": True}

        return cls._render_saved_filters_dialog(
            notification=notification,
            status=getattr(response, "status_code", 500) or 500,
            saved_filters=saved_filters,
        )

    @classmethod
    @auth_required()
    def save_saved_filter(cls):
        try:
            name = request.form.get("name", "").strip()
            if not name:
                return cls._render_saved_filters_dialog({"message": "Saved filter name is required.", "error": True}, 400)
            if len(name) > ASSESS_SAVED_FILTER_NAME_MAX_LENGTH:
                return cls._render_saved_filters_dialog({"message": "Saved filter name must be 80 characters or fewer.", "error": True}, 400)

            filters = cls._extract_assess_filters_from_request()
            if not filters:
                return cls._render_saved_filters_dialog({"message": "Choose at least one filter before saving.", "error": True}, 400)

            saved_filters = cls._get_saved_assess_filters()
            make_default = request.form.get("is_default") == "true"
            matching_filter = next((saved_filter for saved_filter in saved_filters if saved_filter["name"].lower() == name.lower()), None)
            if matching_filter:
                matching_filter["name"] = name
                matching_filter["filters"] = filters
                matching_filter["is_default"] = make_default or matching_filter["is_default"]
            else:
                saved_filters.append({"id": str(uuid.uuid7()), "name": name, "filters": filters, "is_default": make_default})

            if make_default:
                default_id = matching_filter["id"] if matching_filter else saved_filters[-1]["id"]
                for saved_filter in saved_filters:
                    saved_filter["is_default"] = saved_filter["id"] == default_id

            response = cls._update_saved_filters_profile(saved_filters)
            if getattr(response, "ok", False):
                session[ASSESS_SAVED_FILTER_SESSION_KEY] = make_default
            return cls._render_saved_filters_mutation_response(response, "Assess filter saved.", saved_filters)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to save assess filter.")
            return cls._render_saved_filters_dialog({"message": "Failed to save assess filter.", "error": True}, 500)

    @classmethod
    @auth_required()
    def set_saved_filter_default(cls, filter_id: str):
        saved_filters = cls._get_saved_assess_filters()
        default_filter = next((saved_filter for saved_filter in saved_filters if saved_filter["id"] == filter_id), None)
        if not default_filter:
            return cls._render_saved_filters_dialog({"message": "Saved filter not found.", "error": True}, 404)

        clear_default = request.form.get("clear_default") == "true"
        for saved_filter in saved_filters:
            saved_filter["is_default"] = False if clear_default else saved_filter["id"] == filter_id

        response = cls._update_saved_filters_profile(saved_filters)
        if getattr(response, "ok", False):
            session[ASSESS_SAVED_FILTER_SESSION_KEY] = not clear_default
        message = "Assess default cleared." if clear_default else "Assess default saved."
        return cls._render_saved_filters_mutation_response(response, message, saved_filters)

    @classmethod
    @auth_required()
    def delete_saved_filter(cls, filter_id: str):
        saved_filters = cls._get_saved_assess_filters()
        filtered_saved_filters = [saved_filter for saved_filter in saved_filters if saved_filter["id"] != filter_id]
        if len(filtered_saved_filters) == len(saved_filters):
            return cls._render_saved_filters_dialog({"message": "Saved filter not found.", "error": True}, 404)

        response = cls._update_saved_filters_profile(filtered_saved_filters)
        return cls._render_saved_filters_mutation_response(response, "Assess filter deleted.", filtered_saved_filters)

    @classmethod
    @auth_required()
    def submit_search_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        logger.debug(f"Submitting cluster dialog for stories {story_ids}")
        response = CoreApi().api_post("/assess/stories/group", json_data=story_ids)
        return cls.rerender_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required()
    def bulk_action(cls):
        try:
            payload: dict[str, Any] = {request.form.get("action", ""): request.form.get("value")}
            story_action = StoryUpdatePayload(**payload)
            bulk_action = BulkAction(payload=story_action, story_ids=request.form.getlist("story_ids"))
        except ValidationError:
            logger.debug("No story IDs supplied for bulk update. Returning current story list.")
            return cls.rerender_list(notification=cls.render_response_notification({"error": "No stories selected for bulk action."}))
        response = CoreApi().api_post("/assess/stories/bulk_action", json_data=bulk_action.model_dump(mode="json"))
        return cls.rerender_list(notification=cls.get_notification_from_response(response))

    @classmethod
    def _build_pagination_context(
        cls,
        stories: CacheObject | None,
        paging: PagingData,
        request_params: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Prepare pagination metadata and URLs while preserving active filters.
        """
        total_count = stories.total_count if stories else 0
        limit = max(paging.limit or 20, 1)
        total_pages = stories.total_pages if stories else 1

        requested_index = paging.page or 0
        clamped_index = min(max(requested_index, 0), max(total_pages - 1, 0))

        def build_url(page_index: int) -> str:
            params = {key: value[:] for key, value in request_params.items() if value and key != "offset"}
            if page_index <= 0:
                params.pop("page", None)
            else:
                params["page"] = [str(page_index)]
            query_string = urlencode(params, doseq=True)
            base_url = cls.get_base_route()
            return f"{base_url}?{query_string}" if query_string else base_url

        items_on_page = len(stories or [])
        if total_count and items_on_page:
            page_start = clamped_index * limit + 1
            page_end = min(page_start + items_on_page - 1, total_count)
        else:
            page_start = 0
            page_end = 0

        return {
            "infinite_scroll": current_user.profile.infinite_scroll,
            "current_page": clamped_index + 1,
            "total_pages": total_pages,
            "has_previous": clamped_index > 0,
            "has_next": (clamped_index + 1) < total_pages,
            "previous_url": build_url(clamped_index - 1) if clamped_index > 0 else "",
            "next_url": build_url(clamped_index + 1) if (clamped_index + 1) < total_pages else "",
            "page_start": page_start,
            "page_end": page_end,
            "total_count": total_count,
        }

    @classmethod
    def _render_story_list(
        cls,
        paging_data: PagingData,
        request_params: dict[str, list[str]],
        selected_story_ids: list[str] | None = None,
    ):
        try:
            items = DataPersistenceLayer().get_objects(cls.model, paging_data=paging_data)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        context = cls.get_view_context(items, error)
        context["pagination"] = cls._build_pagination_context(items, paging_data, request_params)
        context["assess_selection_key"] = cls._build_assess_selection_key(request_params)
        context["selected_story_ids"] = selected_story_ids or []

        return render_template(cls.get_list_template(), **context), 200

    @classmethod
    def rerender_list(cls, notification: str | None = None):
        request_params = request.args.to_dict(flat=False)

        if request.method == "POST" and "HX-Current-URL" in request.headers:
            url = request.headers.get("HX-Current-URL", "")

            parsed_url = urlparse(url)
            request_params = parse_qs(parsed_url.query)

        request_params = cls._get_assess_request_params(request_params)
        paging_data = parse_paging_data(request_params)
        selected_story_ids = request.form.getlist("story_ids") if request.method == "POST" else []
        table, status = cls._render_story_list(paging_data, request_params, selected_story_ids=selected_story_ids)
        if notification:
            return make_response(notification + table, status)
        return make_response(table, status)

    @classmethod
    def list_view(cls):
        raw_request_params = request.args.to_dict(flat=False)
        if not is_htmx_request():
            filtered_request_params = {
                key: [value for value in values if value not in (None, "")] for key, values in raw_request_params.items()
            }
            has_reset = "reset" in filtered_request_params
            filtered_request_params.pop("reset", None)
            if not has_reset and not filtered_request_params:
                saved_defaults = cls._get_default_assess_saved_filter_params()
                if saved_defaults:
                    session[ASSESS_SAVED_FILTER_SESSION_KEY] = True
                    return redirect(cls._build_assess_filters_url(saved_defaults))

        request_params = cls._get_assess_request_params(raw_request_params)
        paging_data = parse_paging_data(request_params)
        return cls._render_story_list(paging_data, request_params)

    @classmethod
    def get_item_context(cls, object_id: str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        context["_show_sidebar"] = False
        context["form_action"] = f"hx-post={url_for('assess.story_edit', story_id=object_id)}"
        story = context.get("story")

        if isinstance(story, Story):
            attributes = story.attributes or []
            context["has_rt_id"] = any(isinstance(attr, dict) and attr.get("key") == "rt_id" for attr in attributes)

            cybersecurity_value = next(
                (attr.get("value") for attr in attributes if isinstance(attr, dict) and attr.get("key") == "cybersecurity"),
                None,
            )
            context["story_cyber_status"] = cls._format_cyber_status(cybersecurity_value)
            context["cyber_chip_class"] = cls._get_cyber_chip_class(context["story_cyber_status"])
            context["layout"] = request.args.get("layout", "advanced" if current_user.profile.advanced_story_options else "simple")
            sources = list(cls.get_filter_lists().sources)
            source_dict = {source.id: source for source in sources if source.id}
            cls._enhance_story_with_details(story, source_dict)
        else:
            context["has_rt_id"] = False
            context["story_cyber_status"] = "Not Classified"
            context["cyber_chip_class"] = "badge badge-outline"

        return context

    @staticmethod
    def _format_cyber_status(status: str | None) -> str:
        if not status:
            return "Not Classified"
        normalized = status.strip().lower()
        labels = {
            "yes": "Yes",
            "no": "No",
            "mixed": "Mixed",
            "incomplete": "Incomplete",
            "none": "Not Classified",
        }
        return labels.get(normalized, normalized.capitalize())

    @staticmethod
    def _get_cyber_chip_class(status: str) -> str:
        mapping = {
            "Yes": "badge badge-success badge-lg",
            "No": "badge badge-error badge-lg",
            "Mixed": "badge badge-secondary badge-lg",
            "Incomplete": "badge badge-warning badge-lg",
            "Not Classified": "badge badge-outline badge-lg",
        }
        return mapping.get(status, "badge badge-outline badge-lg")

    @classmethod
    @auth_required()
    def story_view(cls, story_id: str):
        return render_template("assess/story_view.html", **cls.get_item_context(story_id)), 200

    @classmethod
    @auth_required()
    def trigger_bot_action(cls, story_id: str):
        bot_id = request.form.get("bot_id")
        if not bot_id:
            notification = {"message": "Bot identifier is required.", "error": True}
            return render_template("notification/index.html", notification=notification), 400

        api = CoreApi()
        try:
            response = api.api_post("/assess/stories/botactions", json_data={"story_id": story_id, "bot_id": bot_id})
            payload = response.json()
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to decode bot action response.")
            notification = {"message": "Failed to decode bot action response", "error": True}
            notification_html = render_template("notification/index.html", notification=notification)
            return make_response(notification_html, 400)

        notification_html = render_template(
            "notification/index.html",
            notification=cls.get_notification_from_dict(payload),
        )
        content = StoryView._get_action_response_content(story_id)
        return make_response(notification_html + content, 200)

    @staticmethod
    @auth_required()
    def get_tags():
        query = request.args.get("q", "")
        api = CoreApi()
        try:
            tags = api.api_get(f"/assess/taglist?search={query}")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to fetch tag suggestions.")
            tags = []
        return render_template("assess/sidebar/tags_suggestions.html", suggested_tags=tags), 200

    @classmethod
    @auth_required()
    def news_item_view(cls, news_item_id: str = "0"):
        news_item = DataPersistenceLayer().get_object(NewsItem, news_item_id) if news_item_id != "0" else NewsItem.model_construct(id="")
        return render_template("assess/news_item_create.html", news_item=news_item), 200

    @classmethod
    def _handle_news_item_response(
        cls,
        core_response,
        *,
        content_builder: Callable[[str], str] | None = None,
        redirect_on_story: bool = False,
        status_override: int | None = None,
    ) -> ResponseReturnValue:
        try:
            payload = core_response.json()
            story_id = payload.get("story_id", "")
            if not story_id and (story_ids := payload.get("story_ids")):
                story_id = story_ids[0] if isinstance(story_ids, list) else story_ids
        except Exception:
            story_id = ""

        notification = cls.get_notification_from_response(core_response)
        status = status_override if status_override is not None else 200 if getattr(core_response, "ok", False) else 400

        if redirect_on_story and story_id:
            response = make_response(notification, status)
            response.headers["HX-Redirect"] = url_for("assess.story_edit", story_id=story_id)
            return response

        content = content_builder(story_id) if content_builder else ""
        return make_response(notification + content, status)

    @classmethod
    def _validation_error_notification(cls, exc: ValidationError, model: type) -> ResponseReturnValue:
        logger.exception(format_pydantic_errors(exc, model))
        notification = {"message": format_pydantic_errors(exc, model), "error": True}
        notification_html = render_template("notification/index.html", notification=notification, oob=False)
        response = make_response(notification_html, 400)
        response.headers["HX-Retarget"] = "#notification-bar"
        response.headers["HX-Reswap"] = "outerHTML"
        return response

    @classmethod
    def news_item_edit_view(cls, core_response) -> ResponseReturnValue:
        return cls._handle_news_item_response(core_response, redirect_on_story=True)

    @classmethod
    @auth_required()
    def create_news_item(cls):
        logger.debug(f"Creating news item with form fields: {[key for key in request.form.keys() if key != 'csrf_token']}")
        if url := request.form.get("fetch_url"):
            form_data = parse_formdata(request.form)
            return cls._create_news_item_from_url(url, form_data.get("parameters", {}))

        if upload_file := request.files.get("file"):
            return cls._create_news_item_from_file(upload_file)

        item_data = parse_formdata(request.form)
        item_data["collected"] = datetime.datetime.now().isoformat()
        try:
            news_item = NewsItem(**item_data)
        except ValidationError as e:
            return cls._validation_error_notification(e, NewsItem)
        core_response = CoreApi().api_post("/assess/news-items", json_data=news_item.to_core_dict())
        return cls.news_item_edit_view(core_response)

    @classmethod
    @auth_required()
    def update_news_item(cls, news_item_id: str):
        form_data = parse_formdata(request.form)
        try:
            news_item = NewsItem(**form_data)
        except ValidationError as e:
            return cls._validation_error_notification(e, NewsItem)

        core_response = CoreApi().api_put(f"/assess/news-items/{news_item_id}", json_data=news_item.to_core_dict())

        return cls._handle_news_item_response(
            core_response,
            content_builder=lambda _: cls.news_item_view(news_item_id=news_item_id)[0],
        )

    @classmethod
    @auth_required()
    def update_news_item_tags(cls, news_item_id: str):
        form_data = parse_formdata(request.form)
        story_id = str(form_data.get("story_id") or "")
        tags = cls._normalize_news_item_tags(form_data.get("tags") or [])
        try:
            core_response = CoreApi().api_put(f"/assess/news-items/{news_item_id}/tags", json_data=tags)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to update news item tags.")
            return make_response(cls.render_response_notification({"error": "Failed to update news item tags."}), 500)

        notification_html = cls.get_notification_from_response(core_response)
        status = 200 if getattr(core_response, "ok", False) else getattr(core_response, "status_code", 400) or 400
        if not getattr(core_response, "ok", False):
            return make_response(notification_html, status)

        content = cls._get_news_item_tag_update_content(story_id, news_item_id)
        return make_response(notification_html + content, status)

    @staticmethod
    def _normalize_news_item_tags(tags: Any) -> list[dict[str, str]]:
        if isinstance(tags, dict):
            tags = [tags] if "name" in tags else list(tags.values())
        if not isinstance(tags, list):
            return []

        normalized_tags = []
        for tag in tags:
            if isinstance(tag, str):
                name = tag.strip()
                tag_type = "misc"
            elif isinstance(tag, dict):
                name = str(tag.get("name") or "").strip()
                tag_type = str(tag.get("tag_type") or "misc").strip() or "misc"
            else:
                continue

            if name:
                normalized_tags.append({"name": name, "tag_type": tag_type})

        return normalized_tags

    @staticmethod
    def _get_news_item_tag_update_content(story_id: str, news_item_id: str) -> str:
        if not story_id:
            return ""

        story = StoryView.get_object_by_id(story_id)
        if not isinstance(story, Story):
            logger.warning(f"Story {story_id} not found")
            return render_template("partials/404.html")

        news_item = next((item for item in story.news_items or [] if item.id == news_item_id), None)
        if not news_item:
            logger.warning(f"News item {news_item_id} not found on story {story_id}")
            return render_template("partials/404.html")

        return render_template("assess/news_item_card_fragment.html", news_item=news_item, story=story, edit_tags=True)

    @classmethod
    def _create_news_item_from_file(cls, file: FileStorage):
        if file.filename == "":
            flash("No file selected for upload", "error")
            return cls.redirect_htmx(url_for("assess.get_news_item", news_item_id="0"))
        elif file.mimetype not in ["text/plain", "application/json"]:
            flash("Unsupported file type. Please upload a .txt or .json file.", "error")
            return cls.redirect_htmx(url_for("assess.get_news_item", news_item_id="0"))

        try:
            data = file.read()
            json_data = json.loads(data)
            core_response = CoreApi().api_post("/assess/import", json_data=json_data)
            cls.add_flash_notification(core_response)
            return cls.redirect_htmx(url_for("assess.get_news_item", news_item_id=core_response.json().get("id", "0")))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to create news item from file.")
            flash("Failed to create news item from file", "error")

        return cls.redirect_htmx(url_for("assess.get_news_item", news_item_id="0"))

    @classmethod
    @auth_required()
    def import_stories(cls):
        if not (upload_file := request.files.get("file")):
            return make_response(cls.render_response_notification({"error": "No file selected for import."}), 400)

        if upload_file.filename == "":
            return make_response(cls.render_response_notification({"error": "No file selected for import."}), 400)

        try:
            json_data = json.loads(upload_file.read())
            normalized_payload = _normalize_story_import_payload(json_data)
            core_response = CoreApi().api_post("/assess/import", json_data=normalized_payload)
        except JSONDecodeError:
            logger.warning("Failed to decode story import JSON payload.")
            return make_response(cls.render_response_notification({"error": "Invalid JSON file."}), 400)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to import stories.")
            return make_response(cls.render_response_notification({"error": "Failed to import stories."}), 500)

        if not getattr(core_response, "ok", False):
            status_code = getattr(core_response, "status_code", 500) or 500
            try:
                notification_html = cls.get_notification_from_response(core_response)
            except Exception:
                notification_html = cls.render_response_notification({"error": "Failed to import stories."})
            return make_response(notification_html, status_code)

        imported_count = len(core_response.json().get("imported_stories", []))
        flash(f"Imported {imported_count} stor{'y' if imported_count == 1 else 'ies'} successfully", "success")

        response = make_response("", 204)
        response.headers["HX-Refresh"] = "true"
        return response

    @staticmethod
    def _build_simple_web_collector_payload(url: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        collector_parameters = {key: value for key, value in (parameters or {}).items() if value not in ("", None) and key != "WEB_URL"}
        collector_parameters["WEB_URL"] = url.strip()
        return {
            "id": "manual",
            "type": "simple_web_collector",
            "parameters": collector_parameters,
        }

    @classmethod
    def _create_news_item_from_url(cls, url: str, parameters: dict[str, Any] | None = None):
        try:
            payload = cls._build_simple_web_collector_payload(url, parameters)
            core_response = CoreApi().api_post("/assess/news-items/fetch", json_data=payload)
            return cls.news_item_edit_view(core_response)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to create news item from URL.")
            return cls.render_response_notification({"error": "Failed to create news item from URL."})

    @classmethod
    @auth_required()
    def delete_news_item(cls, news_item_id: str):
        try:
            core_response = CoreApi().api_delete(f"/assess/news-items/{news_item_id}")
        except HTTPException:
            raise
        except Exception:
            return cls.render_response_notification({"error": "Failed to delete news item"})

        payload = core_response.json()
        story_id = payload.get("story_id") or payload.get("story_ids", [""])[0]

        current_url_path = cls._get_current_url_path()
        if story_id and current_url_path in {
            url_for("assess.story", story_id=story_id),
            url_for("assess.story_edit", story_id=story_id),
        }:
            if CoreApi().api_get(f"/assess/stories/{story_id}") is None:
                cls.add_flash_notification(core_response)
                return cls.redirect_htmx(url_for("assess.assess"))

        return cls._handle_news_item_response(
            core_response,
            content_builder=cls._get_action_response_content,
            status_override=200,
        )

    @classmethod
    @auth_required()
    def delete_story(cls, story_id: str):
        try:
            core_response = CoreApi().api_delete(f"/assess/story/{story_id}")
        except HTTPException:
            raise
        except Exception:
            return cls.render_response_notification({"error": "Failed to delete story"})

        if cls._get_current_url_path() == url_for("assess.assess"):
            notification_html = cls.get_notification_from_response(core_response)
            return cls.rerender_list(notification=notification_html)

        cls.add_flash_notification(core_response)
        return cls.redirect_htmx(url_for("assess.assess"))

    @staticmethod
    def _get_current_url_path() -> str:
        if current_url := request.headers.get("HX-Current-URL", ""):
            if parsed_url := urlparse(current_url):
                return parsed_url.path or current_url
        return ""

    @staticmethod
    def _get_action_response_content(story_id: str) -> str:
        current_url = StoryView._get_current_url_path()

        edit_path = url_for("assess.story_edit", story_id=story_id)
        detail_path = url_for("assess.story", story_id=story_id)

        context = StoryView.get_item_context(story_id)
        if not context.get("story"):
            logger.warning(f"Story {story_id} not found")
            return render_template("partials/404.html")
        if current_url == edit_path:
            return render_template(
                "assess/story_edit_content.html",
                **context,
            )
        elif current_url == detail_path:
            return render_template(
                "assess/story.html",
                detail_view=True,
                **context,
            )

        return render_template(
            "assess/story.html",
            detail_view=False,
            **context,
        )

    @classmethod
    @auth_required()
    def ungroup(cls, story_id: str):
        if news_item_ids := request.form.getlist("news_item_ids[]"):
            try:
                response = CoreApi().api_put("/assess/news-items/ungroup", json_data=news_item_ids)
                notification_html = cls.get_notification_from_response(response)
                content = cls._get_action_response_content(story_id)
                return make_response(notification_html + content, 200)
            except HTTPException:
                raise
            except Exception:
                logger.exception("Failed to ungroup news item.")
                return cls.render_response_notification({"error": "Failed to ungroup news item."})
        else:
            try:
                core_response = CoreApi().api_put("/assess/stories/ungroup", json_data=[story_id])
                cls.add_flash_notification(core_response)
                return cls.redirect_htmx(url_for("assess.assess"))
            except HTTPException:
                raise
            except Exception:
                logger.exception("Failed to ungroup story.")
                return cls.render_response_notification({"error": "Failed to ungroup story."})

    @classmethod
    @auth_required()
    def export_stories(cls):
        story_ids = request.args.getlist("story_ids")
        if not story_ids:
            logger.warning("No story IDs provided for export.")
            return cls.render_response_notification({"error": "Failed to export stories."}), 400

        try:
            paging_data = PagingData(query_params={"story_ids": story_ids}, limit=len(story_ids))
            stories = DataPersistenceLayer().get_objects(Story, paging_data)
            export_data = [story.to_core_dict() for story in stories.items]

            response_data = json.dumps({"total_count": len(export_data), "items": export_data}, indent=2)
            flask_response = make_response(response_data, 200)
            flask_response.headers["Content-Type"] = "application/json"
            flask_response.headers["Content-Disposition"] = (
                f'attachment; filename="stories_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            )
            return flask_response
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to export stories.")
            return cls.render_response_notification({"error": "Failed to export stories."}), 500

    @classmethod
    @auth_required()
    def patch_story(cls, story_id: str):
        try:
            form_data = parse_formdata(request.form)
            story_update = StoryUpdatePayload(**form_data)
        except ValidationError as exc:
            return cls._validation_error_notification(exc, StoryUpdatePayload)

        response = CoreApi().api_patch(f"/assess/stories/{story_id}", json_data=story_update.model_dump(mode="json"))
        notification_html = cls.get_notification_from_response(response)

        content = cls._get_action_response_content(story_id)
        return make_response(notification_html + content, 200)

    def get(self, **kwargs) -> tuple[str, int]:
        object_id = kwargs.get("story_id")
        if object_id is None:
            return self.list_view()
        return self.edit_view(object_id=object_id)

    def post(self, *args, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        object_id = kwargs.get("story_id")
        if object_id is None:
            return abort(405)

        return self.patch_story(story_id=object_id)

    def put(self, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        object_id = kwargs.get("story_id")
        if object_id is None:
            return abort(405)

        return self.patch_story(story_id=object_id)

    @staticmethod
    @auth_required()
    def versions_view(story_id: str) -> tuple[str, int] | Response:
        """Display revision history for a story"""
        if not story_id:
            return abort(400, description="No story ID provided.")

        # Get story data
        story = DataPersistenceLayer().get_object(Story, story_id)
        if not story:
            return abort(404, description="Story not found.")

        # Get revisions from core API
        revisions_data = CoreApi().api_get(f"/assess/stories/{story_id}/revisions")
        revisions = revisions_data.get("items", []) if revisions_data else []

        context = {
            "story": story,
            "revisions": revisions,
        }

        return render_template("assess/story_versions.html", **context), 200

    @staticmethod
    @auth_required()
    def diff_view(story_id: str, from_rev: int, to_rev: int) -> tuple[str, int] | Response:
        """Display diff between two story revisions"""
        if not story_id:
            return abort(400, description="No story ID provided.")

        core_api = CoreApi()
        from_revision = core_api.api_get(f"/assess/stories/{story_id}/revisions/{from_rev}")
        to_revision = core_api.api_get(f"/assess/stories/{story_id}/revisions/{to_rev}")
        if not from_revision or not to_revision:
            return abort(404, description="Revision not found.")

        story_title = to_revision.get("data", {}).get("title") or from_revision.get("data", {}).get("title")
        diff = build_story_revision_diff_payload(story_id, story_title, from_revision, to_revision)

        context = {
            "diff": diff,
            "from_rev": from_rev,
            "to_rev": to_rev,
            "story_id": story_id,
        }

        return render_template("assess/story_diff.html", **context), 200
