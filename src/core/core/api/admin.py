from flask_restx import Resource, Namespace, Api

from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag


class AdminSettings(Resource):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return {}, 200

    @auth_required("ADMIN_OPERATIONS")
    def put(self):
        return {"error": "TODO IMPLEMENT"}, 501


class DeleteTags(Resource):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        NewsItemTag.delete_all_tags()
        return {"message": "deleted all tags"}, 200


class UngroupStories(Resource):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


class ResetDatabase(Resource):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


def initialize(api: Api):
    namespace = Namespace("admin", description="Admin operations")

    namespace.add_resource(AdminSettings, "/")
    namespace.add_resource(DeleteTags, "/delete-tags")
    namespace.add_resource(UngroupStories, "/ungroup-stories")
    namespace.add_resource(ResetDatabase, "/reset-database")

    api.add_namespace(namespace, path="/admin")
