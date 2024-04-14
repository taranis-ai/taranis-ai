from flask import Flask
from flask.views import MethodView

from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag


class AdminSettings(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return {}, 200

    @auth_required("ADMIN_OPERATIONS")
    def put(self):
        return {"error": "TODO IMPLEMENT"}, 501


class DeleteTags(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        NewsItemTag.delete_all_tags()
        return {"message": "deleted all tags"}, 200


class UngroupStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


class ResetDatabase(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


def initialize(app: Flask):
    base_route = "/api/admin"
    app.add_url_rule(f"{base_route}/", view_func=AdminSettings.as_view("admin_settings"))
    app.add_url_rule(f"{base_route}/delete-tags", view_func=DeleteTags.as_view("delete_tags"))
    app.add_url_rule(f"{base_route}/ungroup-stories", view_func=UngroupStories.as_view("ungroup_all_stories"))
    app.add_url_rule(f"{base_route}/reset-database", view_func=ResetDatabase.as_view("reset_database"))
