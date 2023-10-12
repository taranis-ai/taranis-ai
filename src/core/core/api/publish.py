from flask import Response, request
from flask_restx import Resource, Namespace, Api

from core.managers import auth_manager, queue_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import auth_required
from core.model import product, publisher_preset, product_type


class ProductTypes(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class Products(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id=None):
        try:
            if product_id:
                return product.Product.get_detail_json(product_id)

            filter_keys = ["search", "range", "sort"]
            filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}

            filter_args["limit"] = min(int(request.args.get("limit", 20)), 200)
            filter_args["offset"] = int(request.args.get("offset", 0))

            return product.Product.get_json(filter_args, auth_manager.get_user_from_jwt())
        except Exception:
            logger.exception("Failed to get Products")
            return {"error": "Failed to get Products"}, 400

    @auth_required("PUBLISH_CREATE")
    def post(self):
        new_product = product.Product.add(request.json)
        return {"message": "New Product created", "id": new_product.id}, 201

    @auth_required("PUBLISH_UPDATE")
    def put(self, product_id):
        return product.Product.update(product_id, request.json)

    @auth_required("PUBLISH_DELETE")
    def delete(self, product_id):
        return product.Product.delete(product_id)


class PublishProduct(Resource):
    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id, publisher_id):
        product_data, status_code = product.Product.generate_product(product_id)
        if status_code == 200:
            return publisher_preset.PublisherPreset.get(publisher_id)
        return {"error": "Failed to generate product"}, status_code


class ProductsRender(Resource):
    @auth_required("PUBLISH_ACCESS")
    def post(self, product_id):
        queue_manager.queue_manager.generate_product(product_id)

        return {"message": "Product is being generated"}, 200

    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id):
        if product_data := product.Product.get_render(product_id):
            return Response(product_data["blob"], headers={"Content-Type": product_data["mime_type"]}, status=200)
        return {"error": f"Product {product_id} not found"}, 404


def initialize(api: Api):
    namespace = Namespace("publish", description="Publish API")
    namespace.add_resource(Products, "/products", "/products/<int:product_id>")
    namespace.add_resource(ProductTypes, "/product-types")
    namespace.add_resource(ProductsRender, "/products/<int:product_id>/render")
    namespace.add_resource(
        PublishProduct,
        "/products/<int:product_id>/publishers/<string:publisher_id>",
    )
    api.add_namespace(namespace, path="/publish")
