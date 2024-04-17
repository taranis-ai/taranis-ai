from flask import request, Flask
from flask.views import MethodView
from datetime import datetime, timedelta

from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import api_key_required
from core.model import news_item, word_list, bot


class BotGroupAction(MethodView):
    @api_key_required
    def put(self):
        aggregate_ids = request.json
        if not aggregate_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_aggregate(aggregate_ids)
        sse_manager.news_items_updated()
        return response, code


class BotGroupMultipleAction(MethodView):
    @api_key_required
    def put(self):
        aggregate_ids = request.json
        if not aggregate_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_multiple_aggregate(aggregate_ids)
        sse_manager.news_items_updated()
        return response, code


class BotUnGroupAction(MethodView):
    @api_key_required
    def put(self):
        newsitem_ids = request.json
        if not newsitem_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.remove_news_items_from_story(newsitem_ids)
        sse_manager.news_items_updated()
        return response, code


class NewsItemData(MethodView):
    @api_key_required
    def get(self, news_item_data_id=None):
        try:
            if news_item_data_id:
                return news_item.NewsItemData.get_for_api(news_item_data_id)
            filtre_args = {"limit": request.args.get("limit", default=(datetime.now() - timedelta(weeks=1)).isoformat())}
            return news_item.NewsItemData.get_all_for_api(filtre_args)
        except Exception as e:
            logger.error(str(e))
            return {"error": str(e)}, 400

    @api_key_required
    def put(self, news_item_data_id):
        try:
            if not request.json:
                return {"Not update data provided"}
            if language := request.json.get("language"):
                return news_item.NewsItemData.update_news_item_lang(news_item_data_id, language)
            return {"Not implemented"}
        except Exception as e:
            logger.error(str(e))
            return {"error": str(e)}, 400


class UpdateNewsItemAttributes(MethodView):
    @api_key_required
    def put(self, news_item_data_id):
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class UpdateNewsItemsAggregateSummary(MethodView):
    @api_key_required
    def put(self, story_id):
        return news_item.NewsItemAggregate.update(story_id, request.json)


class WordListEntries(MethodView):
    @api_key_required
    def put(self, word_list_id):
        return word_list.WordList.update(word_list_id, request.json)


class BotsInfo(MethodView):
    @api_key_required
    def get(self, bot_id=None):
        if bot_id:
            return bot.Bot.get_by_filter(bot_id)
        search = request.args.get(key="search", default=None)
        return bot.Bot.get_all_json(search)

    @api_key_required
    def put(self, bot_id):
        if bot_result := bot.Bot.update(bot_id, request.json):
            return {"message": f"Bot {bot_result['name']} updated", "id": bot_result["id"]}, 200
        return {"message": f"Bot {bot_id} not found"}, 404


def initialize(app: Flask):
    base_route = "/api/bots"
    app.add_url_rule(f"{base_route}", view_func=BotsInfo.as_view("bots"))
    app.add_url_rule(f"{base_route}/", view_func=BotsInfo.as_view("bots_info"))
    app.add_url_rule(f"{base_route}/<string:bot_id>", view_func=BotsInfo.as_view("bot_info"))
    app.add_url_rule(f"{base_route}/news-item-data", view_func=NewsItemData.as_view("news_item_data"))
    app.add_url_rule(
        f"{base_route}/news-item-data/<string:news_item_data_id>",
        view_func=NewsItemData.as_view("update_news_item_data"),
    )
    app.add_url_rule(
        f"{base_route}/news-item-data/<string:news_item_data_id>/attributes",
        view_func=UpdateNewsItemAttributes.as_view("update_news_item_attributes"),
    )
    app.add_url_rule(
        f"{base_route}/stories/group",
        view_func=BotGroupAction.as_view("group_stories"),
    )
    app.add_url_rule(
        f"{base_route}/stories/group-multiple",
        view_func=BotGroupMultipleAction.as_view("group_multiple_stories"),
    )
    app.add_url_rule(
        f"{base_route}/stories/ungroup",
        view_func=BotUnGroupAction.as_view("ungroup_stories_bot"),
    )
    app.add_url_rule(
        f"{base_route}/story/<string:story_id>/summary",
        view_func=UpdateNewsItemsAggregateSummary.as_view("update_aggregate_summary"),
    )
    app.add_url_rule(
        f"{base_route}/word-list/<int:word_list_id>",
        view_func=WordListEntries.as_view("word_list_entries"),
    )
