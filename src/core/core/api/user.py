from flask_restx import Resource, Namespace, Api
from flask import request

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import word_list, product_type, publisher_preset
from core.model.user import User
from core.managers.log_manager import logger


class UserProfile(Resource):
    def get(self):
        if user := auth_manager.get_user_from_jwt():
            return user.get_profile_json()
        return {"message": "User not found"}, 404

    def put(self):
        # sourcery skip: assign-if-exp, reintroduce-else, swap-if-else-branches, use-named-expression
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"message": "User not found"}, 404
        json_data = request.json
        if not json_data:
            return {"message": "No input data provided"}, 400
        return User.update_profile(user, request.json)


class UserProductTypes(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), False)


class UserPublisherPresets(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return publisher_preset.PublisherPreset.get_all_json(None)


def initialize(api: Api):
    namespace = Namespace("users", description="User API", path="/api/v1/users")

    namespace.add_resource(UserProfile, "/profile")
    namespace.add_resource(UserProductTypes, "/my-product-types")
    namespace.add_resource(UserPublisherPresets, "/my-publisher-presets")
    api.add_namespace(namespace)
