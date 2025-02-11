from flask import Blueprint, request, Flask
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.model import product_type, product
from core.service.product import ProductService
from core.config import Config


class ProductTypes(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_for_api(None, with_count=False, user=current_user)


class Products(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id: str | None = None):
        if product_id:
            return product.Product.get_for_api(product_id)

        filter_keys = ["search", "range", "sort"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}

        filter_args["limit"] = min(int(request.args.get("limit", 20)), 200)
        filter_args["offset"] = int(request.args.get("offset", 0))

        return product.Product.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("PUBLISH_CREATE")
    def post(self):
        new_product = product.Product.add(request.json)
        return {"message": "New Product created", "id": new_product.id}, 201

    @auth_required("PUBLISH_UPDATE")
    def put(self, product_id: str):
        return product.Product.update(product_id, request.json)

    @auth_required("PUBLISH_DELETE")
    def delete(self, product_id: str):
        return product.Product.delete(product_id)


class PublishProduct(MethodView):
    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id: str, publisher_id: str):
        return queue_manager.queue_manager.publish_product(product_id, publisher_id)


class ProductsRender(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def post(self, product_id: str):
        return queue_manager.queue_manager.generate_product(product_id)

    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id: str):
        return ProductService.get_render(product_id)


def initialize(app: Flask):
    publish_bp = Blueprint("publish", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/publish")

    publish_bp.add_url_rule("/products/<string:product_id>/render", view_func=ProductsRender.as_view("render_product"))
    publish_bp.add_url_rule(
        "/products/<string:product_id>/publishers/<string:publisher_id>", view_func=PublishProduct.as_view("publish_product")
    )
    publish_bp.add_url_rule("/products", view_func=Products.as_view("products"))
    publish_bp.add_url_rule("/products/<string:product_id>", view_func=Products.as_view("product"))
    publish_bp.add_url_rule("/product-types", view_func=ProductTypes.as_view("product_types"))

    app.register_blueprint(publish_bp)
