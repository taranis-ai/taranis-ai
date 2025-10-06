from typing import Any
from flask_jwt_extended import current_user
from flask import render_template, request

from models.assess import Story, FilterLists
from models.admin import Connector
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.cache import get_model_from_cache, add_model_to_cache
from frontend.auth import auth_required
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger


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
        return base_context

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "assess/assess_sidebar.html"

    @staticmethod
    def _enhance_story_with_details(story: Story, sources: dict[str, Any]) -> Story:
        if first_news_item := story.news_items[0]:
            if source := sources.get(first_news_item.osint_source_id):
                # Add the source as an pydantic extra field to the story for easier access in the template
                story.__dict__["source"] = source
        return story

    @staticmethod
    def _get_filter_lists() -> FilterLists:
        if filter_lists := get_model_from_cache(FilterLists._model_name, "", current_user.id):
            return filter_lists
        if filter_lists := CoreApi().get_filter_lists():
            add_model_to_cache(filter_lists, "", current_user.id)
            return filter_lists
        return FilterLists(tags=[], sources=[], groups=[])

    @staticmethod
    def _get_story(story_id: str) -> Story | None:
        if story := get_model_from_cache(Story._model_name, story_id, current_user.id):
            return story
        if story := CoreApi().get_story(story_id):
            add_model_to_cache(story, story_id, current_user.id)
            return story
        return None

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
