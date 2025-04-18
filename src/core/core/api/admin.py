import io
from flask import Blueprint, Flask, request, send_file
from flask.views import MethodView
from datetime import datetime

from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag
from core.model.story import Story
from core.service.story import StoryService
from core.model.settings import Settings
from core.managers import queue_manager
from core.config import Config


class DeleteTags(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return NewsItemTag.delete_all()


class DeleteStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        return Story.delete_all()


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


class ExportStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        if request.args.get("metadata", False):
            data = StoryService.export_with_metadata()
        else:
            data = StoryService.export()

        timestamp = datetime.now().isoformat()
        if data is None:
            return {"error": "Unable to export"}, 400
        return send_file(
            io.BytesIO(data),
            download_name=f"story_export_{timestamp}.json",
            mimetype="application/json",
            as_attachment=True,
        )


class SettingsView(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return Settings.get_all_for_api({})

    @auth_required("ADMIN_OPERATIONS")
    def put(self):
        if data := request.json:
            return Settings.update(data)
        return {"error": "No data provided"}, 400

    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        if data := request.json:
            return Settings.update(data)
        return {"error": "No data provided"}, 400


def initialize(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/admin")

    admin_bp.add_url_rule("/delete-tags", view_func=DeleteTags.as_view("delete_tags"))
    admin_bp.add_url_rule("/delete-stories", view_func=DeleteStories.as_view("delete_stories"))
    admin_bp.add_url_rule("/ungroup-stories", view_func=UngroupStories.as_view("ungroup_all_stories"))
    admin_bp.add_url_rule("/reset-database", view_func=ResetDatabase.as_view("reset_database"))
    admin_bp.add_url_rule("/clear-queues", view_func=ClearQueues.as_view("clear_queue"))
    admin_bp.add_url_rule("/export-stories", view_func=ExportStories.as_view("export_stories"))
    admin_bp.add_url_rule("/settings", view_func=SettingsView.as_view("settings"))

    app.register_blueprint(admin_bp)
