from flask_restx import Resource, Namespace
from flask import request

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import word_list, product_type, publisher_preset
from core.model.user import User
from core.managers.log_manager import logger


class UserProfile(Resource):
    def get(self):
        if user := auth_manager.get_user_from_jwt():
            return User.get_profile_json(user)
        return {"message": "User not found"}, 404

    def put(self):
        user = auth_manager.get_user_from_jwt()
        return User.update_profile(user, request.json)


class UserWordLists(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return word_list.WordList.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class UserProductTypes(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), False)


class UserPublisherPresets(Resource):
    @auth_required("PUBLISH_ACCESS")
    def get(self):
        return publisher_preset.PublisherPreset.get_all_json(None)


def initialize(api):
    namespace = Namespace("users", description="User API", path="/api/v1/users")

    namespace.add_resource(UserProfile, "/profile")
    namespace.add_resource(UserWordLists, "/my-word-lists")
    namespace.add_resource(UserProductTypes, "/my-product-types")
    namespace.add_resource(UserPublisherPresets, "/my-publisher-presets")
    api.add_namespace(namespace)
