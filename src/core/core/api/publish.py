import base64
from flask import Response
from flask import request
from flask_restful import Resource

from core.managers import auth_manager, presenters_manager, publishers_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import auth_required, ACLCheck
from core.model import product, product_type, publisher_preset


class Products(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        try:
            filter = {}
            if "search" in request.args and request.args["search"]:
                filter["search"] = request.args["search"]
            if "range" in request.args and request.args["range"]:
                filter["range"] = request.args["range"]
            if "sort" in request.args and request.args["sort"]:
                filter["sort"] = request.args["sort"]

            offset = None
            if "offset" in request.args and request.args["offset"]:
                offset = int(request.args["offset"])

            limit = 50
            if "limit" in request.args and request.args["limit"]:
                limit = min(int(request.args["limit"]), 200)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return product.Product.get_json(filter, offset, limit, auth_manager.get_user_from_jwt())

    @auth_required("PUBLISH_CREATE")
    def post(self):
        user = auth_manager.get_user_from_jwt()
        new_product = product.Product.add_product(request.json, user.id)
        return new_product.id


class Product(Resource):
    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_TYPE_ACCESS)
    def get(self, product_id):
        return product.Product.get_detail_json(product_id)

    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def put(self, product_id):
        product.Product.update_product(product_id, request.json)

    @auth_required("PUBLISH_DELETE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def delete(self, product_id):
        return product.Product.delete(product_id)


class PublishProduct(Resource):
    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id, publisher_id):
        product_data, status_code = presenters_manager.generate_product(product_id)
        if status_code == 200:
            return publishers_manager.publish(
                publisher_preset.PublisherPreset.find(publisher_id),
                product_data,
                None,
                None,
                None,
            )
        else:
            return "Failed to generate product", status_code


class ProductsOverview(Resource):
    def get(self, product_id):
        if "jwt" in request.args:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is not None:
                permissions = user.get_permissions()
                if "PUBLISH_ACCESS" in permissions:
                    if product_type.ProductType.allowed_with_acl(product_id, user, False, True, False):
                        product_data, status_code = presenters_manager.generate_product(product_id)
                        if status_code == 200:
                            return Response(
                                base64.b64decode(product_data["data"]),
                                mimetype=product_data["mime_type"],
                            )
                        else:
                            return "Failed to generate product", status_code
                    else:
                        logger.store_auth_error_activity("Unauthorized access attempt to Product Type")
                else:
                    logger.store_auth_error_activity("Insufficient permissions")
            else:
                logger.store_auth_error_activity("Invalid JWT")
        else:
            logger.store_auth_error_activity("Missing JWT")


def initialize(api):
    api.add_resource(Products, "/api/v1/publish/products")
    api.add_resource(Product, "/api/v1/publish/products/<int:product_id>")
    api.add_resource(ProductsOverview, "/api/v1/publish/products/<int:product_id>/overview")
    api.add_resource(
        PublishProduct,
        "/api/v1/publish/products/<int:product_id>/publishers/<string:publisher_id>",
    )
