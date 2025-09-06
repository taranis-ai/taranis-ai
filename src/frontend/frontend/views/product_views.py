from typing import Any
from flask import render_template

from models.product import Product
from frontend.views.base_view import BaseView
from frontend.filters import render_datetime, render_count, render_item_type
from models.types import PUBLISHER_TYPES
from frontend.core_api import CoreApi
from frontend.log import logger


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

    product_types = [
        {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))} for member in PUBLISHER_TYPES
    ]

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
        base_context["product_types"] = cls.product_types
        return base_context

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        product = context[cls.model_name()]
        context["submit_text"] = f"Update {cls.pretty_name()} - {product.title}"
        context["is_edit"] = product.id is not None and product.id != 0

        return context

    @classmethod
    def product_download(cls, product_id: str):
        error = "Failed to download product"
        try:
            core_resp = CoreApi().download_product(product_id)
            if not core_resp.ok:
                error = core_resp.json().get("error", "Unknown error")

            return CoreApi.stream_proxy(core_resp, "products_export.json")
        except Exception as e:
            logger.error(f"Download product failed: {str(e)}")
            error = f"Failed to download product - {str(e)}"

        return render_template("notification/index.html", notification={"message": error, "error": True}), 400

    @classmethod
    def product_render(cls, product_id: str):
        error = "Failed to render product"
        try:
            core_resp = CoreApi().render_product(product_id)
            if not core_resp.ok:
                error = core_resp.json().get("error", "Unknown error")

            message = core_resp.json().get("message", "Unknown error")
            return render_template("notification/index.html", notification={"message": message, "error": False}), 200
        except Exception as e:
            logger.error(f"Render product failed: {str(e)}")
            error = f"Failed to render product - {str(e)}"

        return render_template("notification/index.html", notification={"message": error, "error": True}), 400
