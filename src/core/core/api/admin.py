from flask import Blueprint, Flask, request, url_for
from flask.views import MethodView

from core.config import Config
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag
from core.model.settings import Settings
from core.model.story import Story
from core.service.admin import AdminService
from core.service.cache_invalidation import cache_invalidation_service, invalidate_frontend_cache_on_success
from core.service.story import StoryService


class DeleteTags(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        response, status = NewsItemTag.delete_all()
        invalidate_frontend_cache_on_success(status, full=True)
        return response, status


class DeleteStories(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        response, status = Story.delete_all()
        invalidate_frontend_cache_on_success(status, full=True)
        return response, status


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


class CacheInvalidate(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode")

        if mode == "all":
            deleted = cache_invalidation_service.invalidate_all()
            return {"message": "Frontend cache invalidated", "deleted": deleted, "mode": mode}, 200

        if mode == "model":
            if not (model_name := str(payload.get("model") or "").strip()):
                return {"error": "model is required for mode=model"}, 400
            deleted = cache_invalidation_service.invalidate_model(model_name, payload.get("object_id"))
            return {"message": "Frontend model cache invalidated", "deleted": deleted, "mode": mode, "model": model_name}, 200

        if mode == "scope":
            if not (scope_name := str(payload.get("scope") or "").strip()):
                return {"error": "scope is required for mode=scope"}, 400
            if scope_name not in cache_invalidation_service.scope_names:
                return {"error": f"Unknown scope: {scope_name}"}, 400
            deleted = cache_invalidation_service.invalidate_scope(scope_name)
            return {"message": "Frontend cache scope invalidated", "deleted": deleted, "mode": mode, "scope": scope_name}, 200

        return {"error": "Invalid mode"}, 400


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
            "delete_tags": url_for("admin.delete_tags"),
            "delete_stories": url_for("admin.delete_stories"),
            "ungroup_stories": url_for("admin.ungroup_all_stories"),
            "reset_database": url_for("admin.reset_database"),
            "clear_queues": url_for("admin.clear_queue"),
            "invalidate_cache": url_for("admin.cache_invalidate"),
            "rebuild_story_search_vectors": url_for("admin.rebuild_story_search_vectors"),
            "export_stories": url_for("admin.export_stories"),
            "update_settings": url_for("admin.settings"),
        }

        return settings_data, return_code

    @auth_required("ADMIN_OPERATIONS")
    def put(self):
        if data := request.json:
            response, status = Settings.update(data)
            invalidate_frontend_cache_on_success(status, models=("settings",))
            return response, status
        return {"error": "No data provided"}, 400

    @auth_required("ADMIN_OPERATIONS")
    def post(self):
        if data := request.json:
            response, status = Settings.update(data)
            invalidate_frontend_cache_on_success(status, models=("settings",))
            return response, status
        return {"error": "No data provided"}, 400


def initialize(app: Flask):
    admin_bp = Blueprint("admin", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/admin")

    admin_bp.add_url_rule("/delete-tags", view_func=DeleteTags.as_view("delete_tags"))
    admin_bp.add_url_rule("/delete-stories", view_func=DeleteStories.as_view("delete_stories"))
    admin_bp.add_url_rule("/ungroup-stories", view_func=UngroupStories.as_view("ungroup_all_stories"))
    admin_bp.add_url_rule("/reset-database", view_func=ResetDatabase.as_view("reset_database"))
    admin_bp.add_url_rule("/clear-queues", view_func=ClearQueues.as_view("clear_queue"))
    admin_bp.add_url_rule("/cache/invalidate", view_func=CacheInvalidate.as_view("cache_invalidate"))
    admin_bp.add_url_rule(
        "/rebuild-story-search-vectors",
        view_func=RebuildStorySearchVectors.as_view("rebuild_story_search_vectors"),
    )
    admin_bp.add_url_rule("/export-stories", view_func=ExportStories.as_view("export_stories"))
    admin_bp.add_url_rule("/settings", view_func=SettingsView.as_view("settings"))

    app.register_blueprint(admin_bp)
