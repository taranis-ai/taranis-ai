from base64 import b64decode

from flask import Response
from sqlalchemy import select

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.task import Task


class ProductService:
    @classmethod
    def get_render(cls, product_id: str):
        if render_error := Task.get_failed(product_id):
            logger.debug(f"Failed to render product {product_id}: {render_error.to_dict()}")
            return {"error": render_error.result}, 200
        if product_data := Product.get_render(product_id):
            binary = b64decode(product_data["blob"])
            return Response(
                binary,
                mimetype=product_data["mime_type"],
                headers={"Content-Disposition": f'attachment; filename="{product_data["filename"]}"'},
                status=200,
            )
        return {"error": f"Product {product_id} not found"}, 404

    @classmethod
    def autopublish_product(cls, report_item_id: str):
        products = ProductService.get_products_for_auto_render(report_item_id)
        for product in products:
            if not product.default_publisher:
                logger.warning(f"Product {product.id} is set to auto publish but has no default publisher")
                continue
            if not queue_manager.queue_manager.autopublish_product(product.id, product.default_publisher):
                logger.error(f"Failed to schedule autopublish jobs for product {product.id}")

    @classmethod
    def get_products_for_auto_render(cls, report_item_id: str) -> list[Product]:
        stmt = select(Product).join(Product.report_items).where(Product.auto_publish.is_(True), ReportItem.id == report_item_id).distinct()
        return list(db.session.scalars(stmt).all())
