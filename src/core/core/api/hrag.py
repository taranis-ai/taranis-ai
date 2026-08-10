from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.types import BOT_TYPES

from core.config import Config
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.model.bot import Bot


class HragQuery(MethodView):
    @auth_required("ASSESS_ACCESS")
    def post(self):
        payload = request.get_json(silent=True)
        question = str(payload.get("question") or "").strip() if isinstance(payload, dict) else ""
        if not question:
            return {"error": "question is required"}, 400
        bot = Bot.filter_by_type(BOT_TYPES.HRAG_BOT)
        if bot is None or not bot.enabled:
            return {"error": "HRAG Bot is not enabled"}, 409
        job = queue_manager.queue_manager.enqueue_task("misc", "hrag_query_task", question, bot.id, meta={"user_id": current_user.id})
        if not job:
            return {"error": "Unable to queue HRAG query"}, 503
        return {"task_id": job.id, "status": "queued"}, 202


def initialize(app: Flask):
    hrag_bp = Blueprint("hrag", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/hrag")
    hrag_bp.add_url_rule("/query", view_func=HragQuery.as_view("hrag_query"), methods=["POST"])
    app.register_blueprint(hrag_bp)
