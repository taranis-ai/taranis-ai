from datetime import datetime, timedelta

from flask import Blueprint, Flask, request
from flask.views import MethodView

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_required
from core.managers.db_manager import db
from core.managers.decorators import extract_args
from core.managers.sse_manager import sse_manager
from core.model import bot, news_item, story
from core.service.cache_invalidation import (
    SCOPE_ASSESS_VIEWS,
    SCOPE_SCHEDULE,
    SCOPE_STORY_REPORT_VIEWS,
    SCOPE_STORY_VIEWS,
    invalidate_frontend_cache_on_success,
)


def _bot_actor() -> str:
    return "bot"


class BotGroupAction(MethodView):
    @api_key_required
    def put(self):
        payload = request.json
        story_ids = payload.get("story_ids") if isinstance(payload, dict) else payload
        if not story_ids:
            return {"error": "No story ids provided"}, 400
        response, code = story.Story.group_stories(story_ids, actor=_bot_actor())
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class BotGroupMultipleAction(MethodView):
    @api_key_required
    def put(self):
        payload = request.json
        story_ids = payload.get("story_ids") if isinstance(payload, dict) else payload
        if not story_ids:
            return {"error": "No stories provided"}, 400
        response, code = story.Story.group_multiple_stories(story_ids, actor=_bot_actor())
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class BotUnGroupAction(MethodView):
    @api_key_required
    def put(self):
        payload = request.json
        newsitem_ids = payload.get("newsitem_ids") if isinstance(payload, dict) else payload
        if not newsitem_ids:
            return {"error": "No news items provided"}, 400
        response, code = story.Story.ungroup_news_items_from_story(newsitem_ids, actor=_bot_actor())
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class NewsItem(MethodView):
    @api_key_required
    def get(self, news_item_id: str | None = None):
        try:
            if news_item_id:
                return news_item.NewsItem.get_for_api(news_item_id)
            filtre_args = {"limit": request.args.get("limit", default=(datetime.now() - timedelta(weeks=1)).isoformat())}
            return news_item.NewsItem.get_all_for_api(filtre_args)
        except Exception:
            logger.exception("Failed to get bot news item data")
            return {"error": "Failed to get news item data"}, 400

    @api_key_required
    def put(self, news_item_id):
        try:
            if not request.json:
                return {"error": "No update data provided"}, 400
            if language := request.json.get("language"):
                response, status = news_item.NewsItem.update_news_item_lang(news_item_id, language, actor=_bot_actor())
                invalidate_frontend_cache_on_success(status, scopes=(SCOPE_ASSESS_VIEWS,), object_ids={"news_item": news_item_id})
                return response, status
            return {"error": "Not implemented"}, 501
        except Exception:
            logger.exception("Failed to update bot news item %s", news_item_id)
            return {"error": "Failed to update news item"}, 400


class UpdateNewsItemAttributes(MethodView):
    @api_key_required
    def put(self, news_item_id):
        response, status = news_item.NewsItem.update_attributes(news_item_id, request.json, actor=_bot_actor())
        invalidate_frontend_cache_on_success(
            status,
            scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS),
            object_ids={"news_item": news_item_id},
        )
        return response, status


class StoryAttributes(MethodView):
    @api_key_required
    def get(self, story_id):
        if current_story := story.Story.get(story_id):
            return current_story.attributes
        return {"message": "Story not found"}, 404

    @api_key_required
    def patch(self, story_id):
        if current_story := story.Story.get(story_id):
            if input_data := request.json:
                if isinstance(input_data, dict):
                    input_data = input_data.get("attributes", input_data)
                current_story.patch_attributes(input_data)
                sse_manager.news_items_updated()
            else:
                return {"error": "No data provided"}, 400
            current_story.updated = current_story.utcnow()
            current_story.update_status(change=_bot_actor())
            current_story.record_revision(note="update_story_attributes")
            db.session.commit()
            invalidate_frontend_cache_on_success(200, scopes=(SCOPE_STORY_REPORT_VIEWS,), object_ids={"story": story_id})
            return {"message": "Story updated successfully"}, 200
        return {"error": "Story not found"}, 404


class UpdateStory(MethodView):
    @api_key_required
    def get(self, story_id: str):
        return story.Story.get_for_api(story_id, None)

    @api_key_required
    def put(self, story_id: str):
        result = story.Story.update(story_id, request.json, actor=_bot_actor())
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(result[1], scopes=(SCOPE_STORY_REPORT_VIEWS,), object_ids={"story": story_id})
        return result


class BotsInfo(MethodView):
    @api_key_required
    @extract_args("search")
    def get(self, bot_id=None, filter_args=None):
        if bot_id:
            return bot.Bot.get_for_api(bot_id)
        return bot.Bot.get_all_for_api(filter_args)

    @api_key_required
    def put(self, bot_id):
        if bot_result := bot.Bot.update(bot_id, request.json):
            invalidate_frontend_cache_on_success(200, models=("bot",), scopes=(SCOPE_SCHEDULE,), object_ids={"bot": bot_id})
            return {"message": "Bot updated", "id": bot_result.id}, 200
        return {"message": "Bot not found"}, 404


def initialize(app: Flask):
    bots_bp = Blueprint("bots", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/bots")

    bots_bp.add_url_rule("", view_func=BotsInfo.as_view("bots"))
    bots_bp.add_url_rule("/<string:bot_id>", view_func=BotsInfo.as_view("bot_info"))
    bots_bp.add_url_rule("/news-item", view_func=NewsItem.as_view("bots_news_item"))
    bots_bp.add_url_rule(
        "/news-item/<string:news_item_id>",
        view_func=NewsItem.as_view("update_news_item"),
    )
    bots_bp.add_url_rule(
        "/news-item/<string:news_item_id>/attributes",
        view_func=UpdateNewsItemAttributes.as_view("update_news_item_attributes"),
    )
    bots_bp.add_url_rule(
        "/story/<string:story_id>",
        view_func=UpdateStory.as_view("update_story"),
    )
    bots_bp.add_url_rule(
        "/story/<string:story_id>/attributes",
        view_func=StoryAttributes.as_view("story_attributes"),
    )
    bots_bp.add_url_rule(
        "/stories/group",
        view_func=BotGroupAction.as_view("group_stories"),
    )
    bots_bp.add_url_rule(
        "/stories/group-multiple",
        view_func=BotGroupMultipleAction.as_view("group_multiple_stories"),
    )
    bots_bp.add_url_rule(
        "/stories/ungroup",
        view_func=BotUnGroupAction.as_view("ungroup_stories_bot"),
    )
    app.register_blueprint(bots_bp)
