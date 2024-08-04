from flask import Response

from core.model.product import Product
from core.model.task import Task
from core.log import logger


class ProductService:
    @classmethod
    def get_render(cls, product_id: str):
        if render_error := Task.get_failed(product_id):
            logger.debug(f"Failed to render product {product_id}: {render_error.to_dict()}")
            return {"error": render_error.result}, 200
        if product_data := Product.get_render(product_id):
            return Response(product_data["blob"], headers={"Content-Type": product_data["mime_type"]}, status=200)
        return {"error": f"Product {product_id} not found"}, 404
