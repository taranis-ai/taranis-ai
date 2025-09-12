from typing import Any
from frontend.log import logger

from models.report import ReportItem
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_datetime, render_count, render_item_type
from models.admin import ReportItemType


class ReportItemView(BaseView):
    model = ReportItem
    icon = "presentation-chart-bar"
    htmx_list_template = "analyze/index.html"
    htmx_update_template = "analyze/product.html"
    edit_template = "analyze/product.html"
    default_template = "analyze/index.html"

    base_route = "analyze.analyze"
    edit_route = "analyze.report"
    _read_only = True
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

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        report_types = DataPersistenceLayer().get_objects(ReportItemType)
        base_context["report_types"] = report_types
        return base_context

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        logger.debug(f"Report item context: {context}")
        return context
