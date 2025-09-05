from typing import Any

from models.product import Product
from frontend.views.base_view import BaseView
from frontend.filters import render_datetime, render_count, render_item_type


class ProductView(BaseView):
    model = Product
    icon = "paper-airplane"
    htmx_list_template = "publish/index.html"
    htmx_update_template = "publish/product.html"
    edit_template = "publish/product.html"
    default_template = "publish/index.html"

    base_route = "publish.publish"
    edit_route = "publish.product"
    _read_only = True
    _show_sidebar = False

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Created", "field": "created", "sortable": True, "renderer": render_datetime, "render_args": {"field": "created"}},
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
            {
                "title": "Reports",
                "field": "report_items",
                "sortable": True,
                "renderer": render_count,
                "render_args": {"field": "report_items"},
            },
        ]

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        return base_context
