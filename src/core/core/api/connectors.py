from flask import Blueprint, Flask, request
from flask.views import MethodView


from core.config import Config
from core.managers.auth_manager import auth_required
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

    @auth_required("ASSESS_ACCESS")
    def post(self):
        data = request.json

        if not data:
            return {"error": "resolution is required"}, 400

        response, code = NewsItemConflict.resolve(data)
        return response, code


class StoryInfo(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id):
        if story := Story.get(story_id):
            return {"id": story.id, "title": story.title, "news_item_count": len(story.news_items), "relevance": story.relevance}, 200
        return {"error": "Story not found"}, 404


def initialize(app: Flask):
    conflicts_bp = Blueprint("connectors", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/connectors")

    conflicts_bp.add_url_rule("/conflicts/compare", view_func=StoryConflicts.as_view("story_conflicts"))
    conflicts_bp.add_url_rule("/conflicts/newsitem/compare", view_func=NewsItemConflicts.as_view("news_item_conflicts"))
    conflicts_bp.add_url_rule("/conflict/resolve", view_func=NewsItemConflicts.as_view("news_item_conflict_resolve"))
    conflicts_bp.add_url_rule("/story-summary/<string:story_id>", view_func=StoryInfo.as_view("story_summary"))
    conflicts_bp.add_url_rule("/compare/<string:story_id>", view_func=StoryConflicts.as_view("conflict_by_story_id"))

    conflicts_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(conflicts_bp)
