from flask import Blueprint, Flask, request, url_for
from flask.views import MethodView

from core.config import Config
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag
from core.model.settings import Settings
from core.model.story import Story
from core.service.admin import AdminService
from core.service.story import StoryService


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


class RebuildStorySearchVectors(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        count = StoryService.rebuild_search_vectors()
        return {"message": f"Rebuilt search vectors for {count} stories", "updated": count}, 200


class ExportStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return AdminService.export_stories(request.args)


class SettingsView(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        settings_data, return_code = Settings.get_all_for_api({})
        settings_data["_links"] = {
            "delete_tags": url_for("settings.delete_tags"),
            "delete_stories": url_for("settings.delete_stories"),
            "ungroup_stories": url_for("settings.ungroup_all_stories"),
            "reset_database": url_for("settings.reset_database"),
            "clear_queues": url_for("settings.clear_queue"),
            "rebuild_story_search_vectors": url_for("settings.rebuild_story_search_vectors"),
            "export_stories": url_for("settings.export_stories"),
            "update_settings": url_for("settings.settings"),
        }

        return settings_data, return_code

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
    settings_bp = Blueprint("settings", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/settings")

    settings_bp.add_url_rule("/delete-tags", view_func=DeleteTags.as_view("delete_tags"))
    settings_bp.add_url_rule("/delete-stories", view_func=DeleteStories.as_view("delete_stories"))
    settings_bp.add_url_rule("/ungroup-stories", view_func=UngroupStories.as_view("ungroup_all_stories"))
    settings_bp.add_url_rule("/reset-database", view_func=ResetDatabase.as_view("reset_database"))
    settings_bp.add_url_rule("/clear-queues", view_func=ClearQueues.as_view("clear_queue"))
    settings_bp.add_url_rule(
        "/rebuild-story-search-vectors",
        view_func=RebuildStorySearchVectors.as_view("rebuild_story_search_vectors"),
    )
    settings_bp.add_url_rule("/export-stories", view_func=ExportStories.as_view("export_stories"))
    settings_bp.add_url_rule("/settings", view_func=SettingsView.as_view("settings"))

    app.register_blueprint(settings_bp)
