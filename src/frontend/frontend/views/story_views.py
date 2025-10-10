from typing import Any
from flask_jwt_extended import current_user
from flask import json, render_template, request, url_for
from pydantic import ValidationError
import hashlib

from models.assess import Story, FilterLists, AssessSource
from models.admin import Connector
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.cache import get_model_from_cache, add_model_to_cache
from frontend.auth import auth_required
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.cache_models import PagingData, CacheObject
from frontend.utils.router_helpers import is_htmx_request


class StoryView(BaseView):
    model = Story
    icon = "newspaper"
    htmx_list_template = "assess/story_table.html"
    htmx_update_template = "assess/story.html"
    edit_template = "assess/story_view.html"
    default_template = "assess/index.html"

    base_route = "assess.assess"
    edit_route = "assess.story"
    _show_sidebar = True

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        base_context["filter_lists"] = cls._get_filter_lists()
        if stories := base_context.get("stories"):
            enhanced_stories = cls._get_enhanced_stories(stories, list(base_context["filter_lists"].sources))
            base_context["story_ids"] = [story.id for story in enhanced_stories if getattr(story, "id", None)]
            base_context["stories"] = enhanced_stories
            base_context["actions"] = cls._get_bulk_actions()
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        return "stories"

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "assess/assess_sidebar.html"

    @staticmethod
    def _get_enhanced_stories(stories: CacheObject[Story], sources: list[AssessSource]) -> CacheObject[Story]:
        source_dict = {source.id: source for source in sources if source.id}
        return CacheObject(
            [StoryView._enhance_story_with_details(story, source_dict) for story in stories.items],
            total_count=stories.total_count,
            page=stories.page,
            limit=stories.limit,
            order=stories.order,
        )

    @staticmethod
    def _enhance_story_with_details(story: Story, sources: dict[str, Any]) -> Story:
        if first_news_item := story.news_items[0]:
            if source := sources.get(first_news_item.osint_source_id):
                # Add the source as an pydantic extra field to the story for easier access in the template
                story.source_info = source  # type: ignore
        return story

    @staticmethod
    def _get_filter_lists() -> FilterLists:
        if filter_lists := get_model_from_cache(FilterLists._model_name, "", current_user.id):
            return filter_lists
        if filter_lists_content := CoreApi().get_filter_lists():
            filter_lists = FilterLists(**filter_lists_content)
            add_model_to_cache(filter_lists, "", current_user.id)
            return filter_lists
        return FilterLists(tags=[], sources=[], groups=[])

    @staticmethod
    def _get_story(story_id: str) -> Story | None:
        if story := get_model_from_cache(Story._model_name, story_id, current_user.id):
            return story
        if story_content := CoreApi().get_story(story_id):
            story = Story(**story_content)
            add_model_to_cache(story, story_id, current_user.id)
            return story
        return None

    @staticmethod
    def _get_dict_to_cache_key(filter_args: dict) -> str:
        json_str = json.dumps(filter_args, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(json_str.encode()).hexdigest()

    @staticmethod
    def _get_connectors() -> list[Connector]:
        dpl = DataPersistenceLayer()
        return dpl.get_objects(Connector)

    @classmethod
    @auth_required()
    def get_sharing_dialog(cls) -> str:
        story_id = request.args.get("story_id", "")
        if story := cls._get_story(story_id):
            connectors = cls._get_connectors()
            return render_template("assess/story_sharing_dialog.html", story=story, connectors=connectors)
        return render_template("assess/story_sharing_dialog.html", story=None, connectors=[])

    @classmethod
    @auth_required()
    def submit_sharing_dialog(cls) -> str:
        story_id = request.form.get("story_id", "")
        logger.debug(f"Submitting sharing dialog for story {story_id} - {request.form}")
        return cls.render_response_notification({"message": "Story shared successfully", "category": "success"})

    @classmethod
    @auth_required()
    def bulk_mark_read(cls):
        return cls._handle_bulk_story_update(defaults={"read": True})

    @classmethod
    @auth_required()
    def bulk_mark_important(cls):
        return cls._handle_bulk_story_update(defaults={"important": True})

    @classmethod
    def _handle_bulk_story_update(cls, *, defaults: dict[str, Any]) -> tuple[str, int]:
        payload = request.get_json(silent=True) or {}
        story_ids = payload.get("story_ids") or []
        if not isinstance(story_ids, list) or len(story_ids) == 0:
            logger.debug("No story IDs supplied for bulk update. Returning current story list.")
            return cls.list_view()

        update_payload = {k: v for k, v in payload.items() if k != "story_ids"}
        if not update_payload:
            update_payload = defaults

        api = CoreApi()
        failed_updates: list[str] = []
        for story_id in story_ids:
            response = api.api_put(f"/assess/story/{story_id}", json_data=update_payload)
            if not getattr(response, "ok", False):
                failed_updates.append(story_id)
                logger.warning(f"Failed to update story {story_id} with payload {update_payload}: {getattr(response, 'text', '')}")

        DataPersistenceLayer().invalidate_cache_by_object(Story)

        if failed_updates:
            logger.error(f"Bulk update failed for stories: {failed_updates}")

        return cls.list_view()

    @staticmethod
    def parse_paging_data() -> PagingData:
        """Unmarshal Flask request.args into a PagingData model."""
        args: dict[str, list[str]] = request.args.to_dict(flat=False)

        # Flatten single-value entries for convenience in query_params
        query_params: dict[str, str | list[str]] = {k: v[0] if len(v) == 1 else v for k, v in args.items()}

        # Extract known parameters (convert to correct types if possible)
        def get_int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        page = get_int(query_params.get("page"))
        limit = get_int(query_params.get("limit"))
        order = str(query_params.get("order")) if "order" in query_params else None
        search = str(query_params.get("search")) if "search" in query_params else None

        return PagingData(
            page=page,
            limit=limit,
            order=order,
            search=search,
            query_params=query_params,
        )

    @classmethod
    def _get_bulk_actions(cls) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if mark_read_url := url_for("assess.bulk_mark_read"):
            actions.append(
                {
                    "label": "Mark as read",
                    "icon": "eye",
                    "btn_class": "btn-primary",
                    "hx_post": mark_read_url,
                    "target": "#assess",
                    "swap": "outerHTML",
                    "payload": {"read": True},
                }
            )

        if mark_important_url := url_for("assess.bulk_mark_important"):
            actions.append(
                {
                    "label": "Mark as important",
                    "icon": "star",
                    "btn_class": "btn-outline",
                    "hx_post": mark_important_url,
                    "target": "#assess",
                    "swap": "outerHTML",
                    "payload": {"important": True},
                }
            )

        return actions

    @classmethod
    def list_view(cls):
        logger.debug(f"Got request args: {request.args}")
        request_params = request.args.to_dict(flat=False)
        logger.debug(f"Got request params: {request_params}")
        paging_data = cls.parse_paging_data()
        logger.debug(f"paging data: {paging_data}")

        try:
            items = DataPersistenceLayer().get_objects(cls.model, paging_data=paging_data)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        if error and is_htmx_request():
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("notification/index.html", notification={"message": error, "error": True}), 400

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error)), 200

    @classmethod
    def render_list(cls) -> tuple[str, int]:
        try:
            items = DataPersistenceLayer().get_objects(cls.model)
            status_code = 200
            error = None
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
            status_code = 400
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)
            status_code = 500

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error)), status_code

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        context["_show_sidebar"] = False
        return context
