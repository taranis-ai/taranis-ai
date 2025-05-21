from typing import Any
from models.admin import OSINTSource
from frontend.views.base_view import BaseView
from frontend.filters import render_icon, render_source_parameter, render_state


class SourceView(BaseView):
    model = OSINTSource
    icon = "book-open"
    _index = 63

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Icon", "field": "icon", "sortable": False, "renderer": render_icon},
            {"title": "State", "field": "state", "sortable": False, "renderer": render_state},
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Feed", "field": "parameters", "sortable": True, "renderer": render_source_parameter},
        ]
