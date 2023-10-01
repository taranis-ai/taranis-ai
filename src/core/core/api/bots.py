from flask import request
from flask_restx import Resource, Namespace, Api
from datetime import datetime, timedelta

from core.managers.sse_manager import sse_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import api_key_required
from core.model import news_item, word_list, bot


class BotGroupAction(Resource):
    @api_key_required
    def put(self):
        aggregate_ids = request.json
        if not aggregate_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_aggregate(aggregate_ids)
        sse_manager.news_items_updated()
        return response, code


class BotGroupMultipleAction(Resource):
    @api_key_required
    def put(self):
        aggregate_ids = request.json
        if not aggregate_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_multiple_aggregate(aggregate_ids)
        sse_manager.news_items_updated()
        return response, code


class BotUnGroupAction(Resource):
    @api_key_required
    def put(self):
        newsitem_ids = request.json
        if not newsitem_ids:
            return {"No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.remove_news_items_from_story(newsitem_ids)
        sse_manager.news_items_updated()
        return response, code


class NewsItemData(Resource):
    @api_key_required
    def get(self):
        try:
            limit = request.args.get("limit", default=(datetime.now() - timedelta(weeks=1)).isoformat())
            return news_item.NewsItemData.get_all_news_items_data(limit)
        except Exception:
            logger.log_debug_trace("GET /news-item-data failed")
            return "", 400


class UpdateNewsItemData(Resource):
    @api_key_required
    def put(self, news_item_data_id):
        try:
            if not request.json:
                return {"Not update data provided"}
            if language := request.json.get("language"):
                return news_item.NewsItemData.update_news_item_lang(news_item_data_id, language)
            return {"Not implemented"}
        except Exception:
            logger.log_debug_trace("GET /news-item-data failed")
            return "", 400


class UpdateNewsItemAttributes(Resource):
    @api_key_required
    def put(self, news_item_data_id):
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class UpdateNewsItemTags(Resource):
    @api_key_required
    def put(self, aggregate_id):
        if data := request.json:
            return news_item.NewsItemAggregate.update_tags(aggregate_id, data)
        return {"error": "No data provided"}, 400


class UpdateNewsItemsAggregateSummary(Resource):
    @api_key_required
    def put(self, aggregate_id):
        news_item.NewsItemAggregate.update_news_items_aggregate_summary(aggregate_id, request.json)


class WordListEntries(Resource):
    @api_key_required
    def put(self, word_list_id):
        return word_list.WordList.update(word_list_id, request.json)


class BotsInfo(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return bot.Bot.get_all_json(search)


class BotInfo(Resource):
    def get(self, bot_id):
        return bot.Bot.get_by_filter(bot_id)

    def put(self, bot_id):
        if bot_result := bot.Bot.update(bot_id, request.json):
            return {"message": f"Bot {bot_result['name']} updated", "id": bot_result["id"]}, 200
        return {"message": f"Bot {bot_id} not found"}, 404


def initialize(api: Api):
    namespace = Namespace("bots", description="Bots related operations")
    namespace.add_resource(BotsInfo, "/", "")
    namespace.add_resource(BotInfo, "/<string:bot_id>")
    namespace.add_resource(NewsItemData, "/news-item-data")
    namespace.add_resource(
        UpdateNewsItemTags,
        "/aggregate/<string:aggregate_id>/tags",
    )
    namespace.add_resource(
        UpdateNewsItemData,
        "/news-item-data/<string:news_item_data_id>",
    )
    namespace.add_resource(
        UpdateNewsItemAttributes,
        "/news-item-data/<string:news_item_data_id>/attributes",
    )
    namespace.add_resource(BotGroupAction, "/news-item-aggregates/group")
    namespace.add_resource(BotGroupMultipleAction, "/news-item-aggregates/group-multiple")
    namespace.add_resource(BotUnGroupAction, "/news-item-aggregates/ungroup")

    namespace.add_resource(
        UpdateNewsItemsAggregateSummary,
        "/aggregate/<string:aggregate_id>/summary",
    )
    namespace.add_resource(
        WordListEntries,
        "/word-list/<int:word_list_id>",
    )
    api.add_namespace(namespace, path="/bots")
