from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.config import Config
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.managers.decorators import extract_args
from core.model import product, product_type, publisher_preset
from core.service.cache_invalidation import invalidate_frontend_cache_on_success
from core.service.product import ProductService


class ProductTypes(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_for_api(None, with_count=False, user=current_user)


class PublisherPresets(MethodView):
    @auth_required("PUBLISH_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, preset_id: str | None = None, filter_args: dict | None = None):
        if preset_id:
            return publisher_preset.PublisherPreset.get_for_publish_api(preset_id)
        return publisher_preset.PublisherPreset.get_all_for_publish_api(filter_args)


class Products(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id: str | None = None):
        if product_id:
            return product.Product.get_for_api(product_id)

        filter_keys = ["search", "range", "sort", "page", "limit", "offset"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}

        return product.Product.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("PUBLISH_CREATE")
    def post(self):
        new_product = product.Product.add(request.json)
        invalidate_frontend_cache_on_success(201, models=("product",))
        return {"message": "New Product created", "id": new_product.id, "product": new_product.to_detail_dict()}, 201

    @auth_required("PUBLISH_UPDATE")
    def put(self, product_id: str | None = None):
        if not product_id:
            return {"error": "No product_id provided"}, 400
        response, status = product.Product.update(product_id, request.json)
        invalidate_frontend_cache_on_success(status, models=("product",), object_ids={"product": product_id})
        return response, status

    @auth_required("PUBLISH_DELETE")
    def delete(self, product_id: str | None = None):
        if not product_id:
            return {"error": "No product_id provided"}, 400
        response, status = product.Product.delete(product_id)
        invalidate_frontend_cache_on_success(status, models=("product",), object_ids={"product": product_id})
        return response, status


class PublishProduct(MethodView):
    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id: str, publisher_id: str):
        response, status = queue_manager.queue_manager.publish_product(product_id, publisher_id)
        invalidate_frontend_cache_on_success(status, models=("product",), object_ids={"product": product_id})
        return response, status


class ProductsRender(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def post(self, product_id: str):
        response, status = queue_manager.queue_manager.generate_product(product_id)
        invalidate_frontend_cache_on_success(status, models=("product",), object_ids={"product": product_id})
        return response, status

    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id: str):
        return ProductService.get_render(product_id)


class AutoRenderProducts(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self, report_item_id: str):
        products = ProductService.autopublish_product(report_item_id)
        product_list = [product.to_dict() for product in products]
        return {"products": product_list}, 200


def initialize(app: Flask):
    publish_bp = Blueprint("publish", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/publish")

    publish_bp.add_url_rule("/products/<string:product_id>/render", view_func=ProductsRender.as_view("render_product"))
    publish_bp.add_url_rule(
        "/products/<string:product_id>/publishers/<string:publisher_id>", view_func=PublishProduct.as_view("publish_product")
    )
    publish_bp.add_url_rule("/products", view_func=Products.as_view("products"))
    publish_bp.add_url_rule("/products/<string:product_id>", view_func=Products.as_view("product"), methods=["GET", "PUT", "DELETE"])
    publish_bp.add_url_rule("/product-types", view_func=ProductTypes.as_view("product_types"))
    publish_bp.add_url_rule("/publisher-presets", view_func=PublisherPresets.as_view("publisher_presets"))
    publish_bp.add_url_rule("/publisher-presets/<string:preset_id>", view_func=PublisherPresets.as_view("publisher_preset"))
    publish_bp.add_url_rule("/products/auto-render/<string:report_item_id>", view_func=AutoRenderProducts.as_view("auto_render_products"))
    app.register_blueprint(publish_bp)
