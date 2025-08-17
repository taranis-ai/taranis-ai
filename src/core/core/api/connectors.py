from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.log import logger
from core.config import Config
from core.managers.auth_manager import auth_required
from core.managers.decorators import validate_json
from core.managers.sse_manager import sse_manager
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.news_item_conflict import NewsItemConflict
from core.audit import audit_logger


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

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, story_id):
        if not request.json:
            return {"error": "Invalid JSON payload"}, 400
        if not story_id:
            return {"error": "No story_id provided"}, 400
        resolved_story = request.json.get("resolution", {})
        incoming_story_original = request.json.get("incoming_story_original", {})
        conflict = StoryConflict.conflict_store.get(story_id)
        if conflict is None:
            logger.error(f"No conflict found for story {story_id}")
            return {"error": "No conflict found", "id": story_id}, 404

        response, code = conflict.resolve(resolved_story, user=current_user)
        if code != 200:
            Story.add_or_update(incoming_story_original)
        else:
            NewsItemConflict.reevaluate_conflicts()
        return response, code


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

    @auth_required("ASSESS_CREATE")
    @validate_json
    def post(self):
        data_json = request.json
        if not data_json:
            return {"error": "No NewsItems in JSON Body"}, 422

        result, code = NewsItemConflict.add_news_items_and_clear_from_store(data_json)
        if code != 200:
            return result, code

        sse_manager.news_items_updated()
        return result, 200

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        data = request.json
        if not data:
            return {"error": "Missing story_ids or news_item_ids"}, 400
        result, code = NewsItemConflict.ingest_incoming_ungroup_internal_clear_store(data, current_user)
        sse_manager.news_items_updated()
        return result, code


class StoryInfo(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id):
        if story := Story.get(story_id):
            is_misp_story = any(attribute.key == "misp_event_uuid" for attribute in story.attributes)
            news_item_data = [{"title": item.title, "id": item.id} for item in story.news_items if hasattr(item, "title")]
            return {
                "id": story.id,
                "title": story.title,
                "is_misp_story": is_misp_story,
                "news_item_count": len(story.news_items),
                "relevance": story.relevance,
                "news_item_data": news_item_data,
            }, 200
        return {"error": "Story not found"}, 404


def initialize(app: Flask):
    conflicts_bp = Blueprint("connectors", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/connectors")

    conflicts_bp.add_url_rule("/conflicts/stories", view_func=StoryConflicts.as_view("story_conflicts"))
    conflicts_bp.add_url_rule("/conflicts/stories/<string:story_id>", view_func=StoryConflicts.as_view("story_conflict"))
    conflicts_bp.add_url_rule("/conflicts/news-items", view_func=NewsItemConflicts.as_view("news_item_conflicts"))
    conflicts_bp.add_url_rule("/story-summary/<string:story_id>", view_func=StoryInfo.as_view("story_summary"))

    conflicts_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(conflicts_bp)
