from typing import Any
from flask import render_template, request, Response, abort

from models.product import Product
from models.admin import ProductType
from frontend.views.base_view import BaseView
from frontend.filters import render_datetime, render_count, render_item_type
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.data_persistence import DataPersistenceLayer


class ProductView(BaseView):
    model = Product
    icon = "paper-airplane"
    htmx_list_template = "publish/product_table.html"
    htmx_update_template = "publish/product.html"
    edit_template = "publish/product_view.html"
    default_template = "publish/index.html"

    base_route = "publish.publish"
    edit_route = "publish.product"

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
        product_types = DataPersistenceLayer().get_objects(ProductType)
        base_context["product_types"] = [{"id": pt.id, "name": pt.title} for pt in product_types]
        if cls.model_name() in base_context:
            product: Product = base_context[cls.model_name()]
            is_edit = product.id is not None and product.id != "0"
            if is_edit:
                base_context["submit_text"] = f"Update {cls.pretty_name()} - {product.title}"
            base_context["is_edit"] = is_edit

        return base_context

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

    @classmethod
    def product_publish(cls, product_id: str):
        error = "Failed to publish product"
        try:
            publisher = request.args.get("publisher", "")
            core_resp = CoreApi().publish_product(product_id, publisher_id=publisher)
            if not core_resp.ok:
                error = core_resp.json().get("error", "Unknown error")

            message = core_resp.json().get("message", "Unknown error")
            return render_template("notification/index.html", notification={"message": message, "error": False}), 200
        except Exception as e:
            logger.error(f"Publish product failed: {str(e)}")
            error = f"Failed to publish product - {str(e)}"

        return render_template("notification/index.html", notification={"message": error, "error": True}), 400

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | Response:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            abort(405)
        return self.update_view(object_id=object_id)
