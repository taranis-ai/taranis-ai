from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.config import Config
from core.log import logger
from core.managers.auth_manager import auth_required
from core.managers.decorators import validate_json
from core.managers.sse_manager import sse_manager
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.news_item_conflict import NewsItemConflict
from core.audit import audit_logger


class NewsItems(MethodView):
    @auth_required("ASSESS_CREATE")
    @validate_json
    def post(self):
        data_json = request.json
        if not data_json:
            return {"error": "No NewsItems in JSON Body"}, 422
        logger.debug(data_json)

        news_items = data_json.get("news_items", [])
        resolved_conflict_ids = data_json.get("resolved_conflict_item_ids", [])
        added_ids = []

        for item in news_items:
            result, status = Story.add_single_news_item(item)
            if status == 200:
                added_ids.extend(result.get("news_item_ids", []))
            else:
                logger.error(f"Failed to add news item: {result}")
                return result, status

        NewsItemConflict.remove_by_news_item_ids(resolved_conflict_ids)

        sse_manager.news_items_updated()
        return {"added": added_ids}, 200


class StoryConflicts(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id=None):
        if story_id:
            if conflict := StoryConflict.conflict_store.get(story_id):
                return {
                    "storyId": conflict.story_id,
                    "original": conflict.original,
                    "updated": conflict.updated,
                    "hasProposals": conflict.has_proposals,
                }, 200
        conflicts = [
            {
                "storyId": conflict.story_id,
                "original": conflict.original,
                "updated": conflict.updated,
                "hasProposals": conflict.has_proposals,
            }
            for conflict in StoryConflict.conflict_store.values()
        ]
        return {"conflicts": conflicts}, 200

    @auth_required("ASSESS_ACCESS")
    def put(self):
        data = request.json
        if not data:
            return {"error": "resolution is required"}, 400
        for news_item in data.get("news_items", []):
            if not data.get("news_items"):
                return {"error": "news item is required"}, 400
            Story.add_from_news_item(news_item)
        return {"message": "New news items added successfully"}, 200


class NewsItemConflicts(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        conflicts = [
            {
                "incoming_story_id": conflict.incoming_story_id,
                "news_item_id": conflict.news_item_id,
                "existing_story_id": conflict.existing_story_id,
                "incoming_story": conflict.incoming_story_data,
            }
            for conflict in NewsItemConflict.conflict_store.values()
        ]
        return {"conflicts": conflicts}, 200

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        data = request.json
        if not data:
            return {"error": "Missing story_ids or news_item_ids"}, 400
        response, code = NewsItemConflict.ingest_incoming_ungroup_internal(data, current_user)
        sse_manager.news_items_updated()
        return response, code


class StoryInfo(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id):
        if story := Story.get(story_id):
            news_item_titles = [{"title": item.title, "id": item.id} for item in story.news_items if hasattr(item, "title")]
            return {
                "id": story.id,
                "title": story.title,
                "news_item_count": len(story.news_items),
                "relevance": story.relevance,
                "news_item_titles": news_item_titles,
            }, 200
        return {"error": "Story not found"}, 404


def initialize(app: Flask):
    conflicts_bp = Blueprint("connectors", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/connectors")

    conflicts_bp.add_url_rule("/conflicts/stories", view_func=StoryConflicts.as_view("story_conflicts"))
    conflicts_bp.add_url_rule("/conflicts/stories/<string:story_id>", view_func=StoryConflicts.as_view("story_conflict"))
    conflicts_bp.add_url_rule("/conflicts/news-items", view_func=NewsItemConflicts.as_view("news_item_conflicts"))
    conflicts_bp.add_url_rule("/story-summary/<string:story_id>", view_func=StoryInfo.as_view("story_summary"))
    conflicts_bp.add_url_rule("/news-items", view_func=NewsItems.as_view("news_items"))

    conflicts_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(conflicts_bp)
