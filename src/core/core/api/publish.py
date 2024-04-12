from flask import Response, request, Flask
from flask.views import MethodView

from core.managers import auth_manager, queue_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model import product, product_type


class ProductTypes(MethodView):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class Products(MethodView):
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


class PublishProduct(MethodView):
    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id, publisher_id):
        return queue_manager.queue_manager.publish_product(product_id, publisher_id)


class ProductsRender(MethodView):
    @auth_required("PUBLISH_ACCESS")
    async def post(self, product_id):
        # return await queue_manager.queue_manager.generate_product(product_id)
        logger.info(f"Generating Product {product_id} scheduled")
        return {"message": f"Generating Product {product_id} scheduled"}, 200

    @auth_required("PUBLISH_ACCESS")
    def get(self, product_id):
        if product_data := product.Product.get_render(product_id):
            return Response(product_data["blob"], headers={"Content-Type": product_data["mime_type"]}, status=200)
        return {"error": f"Product {product_id} not found"}, 404


def initialize(app: Flask):
    base_route = "/api/publish"
    app.add_url_rule(f"{base_route}/products/<int:product_id>/render", view_func=ProductsRender.as_view("products_render"))
    app.add_url_rule(
        f"{base_route}/products/<int:product_id>/publishers/<string:publisher_id>", view_func=PublishProduct.as_view("publish_product")
    )
    app.add_url_rule(f"{base_route}/products", view_func=Products.as_view("products"))
    app.add_url_rule(f"{base_route}/products/<int:product_id>", view_func=Products.as_view("product"))
    app.add_url_rule(f"{base_route}/product-types", view_func=ProductTypes.as_view("product_types"))
