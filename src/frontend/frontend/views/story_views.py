from typing import Any

from models.assess import Story
from frontend.views.base_view import BaseView
from frontend.filters import render_datetime, render_count, render_item_type


class StoryView(BaseView):
    model = Story
    icon = "newspaper"
    htmx_list_template = "assess/story_table.html"
    htmx_update_template = "assess/story.html"
    edit_template = "assess/story_view.html"
    default_template = "assess/index.html"

    base_route = "assess.assess"
    edit_route = "assess.story"
    _read_only = False
    _show_sidebar = False

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Created", "field": "created", "sortable": True, "renderer": render_datetime, "render_args": {"field": "created"}},
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
            {
                "title": "Stories",
                "field": "stories",
                "sortable": True,
                "renderer": render_count,
                "render_args": {"field": "stories"},
            },
        ]
