from flask import Blueprint, request, Flask
from flask.views import MethodView
from datetime import datetime, timedelta

from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import api_key_required
from core.model import news_item, bot, story
from core.managers.decorators import extract_args
from core.config import Config


class BotGroupAction(MethodView):
    @api_key_required
    def put(self):
        story_ids = request.json
        if not story_ids:
            return {"No story ids provided"}, 400
        response, code = story.Story.group_stories(story_ids)
        sse_manager.news_items_updated()
        return response, code


class BotGroupMultipleAction(MethodView):
    @api_key_required
    def put(self):
        story_ids = request.json
        if not story_ids:
            return {"No stories provided"}, 400
        response, code = story.Story.group_multiple_stories(story_ids)
        sse_manager.news_items_updated()
        return response, code


class BotUnGroupAction(MethodView):
    @api_key_required
    def put(self):
        newsitem_ids = request.json
        if not newsitem_ids:
            return {"No news items provided"}, 400
        response, code = story.Story.remove_news_items_from_story(newsitem_ids)
        sse_manager.news_items_updated()
        return response, code


class NewsItem(MethodView):
    @api_key_required
    def get(self, news_item_id=None):
        try:
            if news_item_id:
                return news_item.NewsItem.get_for_api(news_item_id)
            filtre_args = {"limit": request.args.get("limit", default=(datetime.now() - timedelta(weeks=1)).isoformat())}
            return news_item.NewsItem.get_all_for_api(filtre_args)
        except Exception as e:
            logger.error(str(e))
            return {"error": str(e)}, 400

    @api_key_required
    def put(self, news_item_id):
        try:
            if not request.json:
                return {"Not update data provided"}
            if language := request.json.get("language"):
                return news_item.NewsItem.update_news_item_lang(news_item_id, language)
            return {"Not implemented"}
        except Exception as e:
            logger.error(str(e))
            return {"error": str(e)}, 400


class UpdateNewsItemAttributes(MethodView):
    @api_key_required
    def put(self, news_item_id):
        return news_item.NewsItem.update_attributes(news_item_id, request.json)


class StoryAttributes(MethodView):
    @api_key_required
    def get(self, story_id):
        if current_story := story.Story.get(story_id):
            return current_story.attributes
        return {"message": f"Story {story_id} not found"}, 404

    @api_key_required
    def patch(self, story_id):
        if current_story := story.Story.get(story_id):
            if input_data := request.json:
                current_story.patch_attributes(input_data)
            else:
                return {"error": "No data provided"}, 400
            return {"message": f"Story {story_id} updated successfully"}, 200
        return {"error": f"Story {story_id} not found"}, 404


class UpdateStory(MethodView):
    @api_key_required
    def get(self, story_id):
        return story.Story.get_for_api(story_id, None)

    @api_key_required
    def put(self, story_id):
        return story.Story.update(story_id, request.json)


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
            return {"message": f"Bot {bot_result.name} updated", "id": bot_result.id}, 200
        return {"message": f"Bot {bot_id} not found"}, 404


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
