from flask import Blueprint, Flask
from flask.views import MethodView

from core.config import Config
from core.managers.auth_manager import auth_required
from core.model.story import StoryConflict
from core.audit import audit_logger


class Connectors(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id=None):
        if story_id:
            if conflict := StoryConflict.conflict_store.get(story_id):
                return conflict.to_dict(), 200
            return {"error": f"Conflict with story id {story_id} not found"}, 404
        conflicts = [
            {
                "storyId": conflict.story_id,
                "original": conflict.original,
                "updated": conflict.updated,
            }
            for conflict in StoryConflict.conflict_store.values()
        ]
        return {"conflicts": conflicts}, 200


def initialize(app: Flask):
    conflicts_bp = Blueprint("connectors", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/connectors")

    conflicts_bp.add_url_rule("/conflicts/compare", view_func=Connectors.as_view("conflicts"))
    conflicts_bp.add_url_rule("/compare/<string:story_id>", view_func=Connectors.as_view("conflict_by_story_id"))

    conflicts_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(conflicts_bp)
