from typing import Any
from flask_jwt_extended import current_user
from flask import json, render_template, request
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
from frontend.cache_models import PagingData


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
            base_context["stories"] = cls._get_enhanced_stories(stories, list(base_context["filter_lists"].sources))
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        return "stories"

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "assess/assess_sidebar.html"

    @staticmethod
    def _get_enhanced_stories(stories: list[Story], sources: list[AssessSource]) -> list[Story]:
        source_dict = {source.id: source for source in sources if source.id}
        return [StoryView._enhance_story_with_details(story, source_dict) for story in stories]

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
        return cls.get_notification_from_dict({"message": "Story shared successfully", "category": "success"})

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
    def list_view(cls):
        logger.debug(f"Got request args: {request.args}")
        request_params = request.args.to_dict(flat=False)
        logger.debug(f"Got request params: {request_params}")
        paging_data = cls.parse_paging_data()
        logger.debug(f"paging data: {paging_data}")
        # page = PagingData(**request_params)
        # logger.debug(f"paging data: {page}")

        return super().list_view()

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
