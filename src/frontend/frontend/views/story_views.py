from typing import Any
from flask_jwt_extended import current_user

from models.assess import Story, FilterLists
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.cache import get_model_from_cache, add_model_to_cache


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
    def _get_filter_lists() -> FilterLists:
        if filter_lists := get_model_from_cache(FilterLists._model_name, current_user.id):  # type: ignore
            return filter_lists
        if filter_lists := CoreApi().get_filter_lists():
            add_model_to_cache(filter_lists, current_user.id)
            return filter_lists
        return FilterLists(tags=[], sources=[], groups=[])
