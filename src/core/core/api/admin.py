from flask import Blueprint, Flask
from flask.views import MethodView

from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag
from core.managers import queue_manager


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
        return NewsItemTag.delete_all()


class UngroupStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


class ResetDatabase(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return {"error": "TODO IMPLEMENT"}, 501


class ClearQueues(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        queue_manager.queue_manager.clear_queues()
        return {"message": "All queues cleared"}, 200


def initialize(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

    admin_bp.add_url_rule("/", view_func=AdminSettings.as_view("admin_settings"))
    admin_bp.add_url_rule("/delete-tags", view_func=DeleteTags.as_view("delete_tags"))
    admin_bp.add_url_rule("/ungroup-stories", view_func=UngroupStories.as_view("ungroup_all_stories"))
    admin_bp.add_url_rule("/reset-database", view_func=ResetDatabase.as_view("reset_database"))
    admin_bp.add_url_rule("/clear-queues", view_func=ClearQueues.as_view("clear_queue"))

    app.register_blueprint(admin_bp)
