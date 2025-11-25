from flask import Response

from core.model.product import Product
from core.model.task import Task
from core.log import logger

from sqlalchemy import select
from core.managers.db_manager import db
from core.model.report_item import ReportItem


class ProductService:
    @classmethod
    def get_render(cls, product_id: str):
        if render_error := Task.get_failed(product_id):
            logger.debug(f"Failed to render product {product_id}: {render_error.to_dict()}")
            return {"error": render_error.result}, 200
        if product_data := Product.get_render(product_id):
            return Response(product_data["blob"], headers={"Content-Type": product_data["mime_type"]}, status=200)
        return {"error": f"Product {product_id} not found"}, 404

    @classmethod
    def get_products_for_auto_render(cls, report_item_id: str) -> list[Product]:
        stmt = select(Product).join(Product.report_items).where(Product.auto_publish.is_(True), ReportItem.id == report_item_id).distinct()
        return db.session.scalars(stmt).all()
