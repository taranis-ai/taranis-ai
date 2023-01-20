from flask import request
import json
from flask_restful import Resource, reqparse
from datetime import datetime, timedelta

from core.managers import sse_manager, bots_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import api_key_required
from core.model import news_item, word_list, bots_node


class BotGroupAction(Resource):
    @api_key_required
    def put(self):
        response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, None)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code


class NewsItemData(Resource):
    @api_key_required
    def get(self):
        try:
            limit = datetime.strftime(datetime.now() - timedelta(weeks=1), "%d.%m.%Y - %H:%M")
            if "limit" in request.args:
                limit = request.args["limit"]
        except Exception:
            logger.log_debug_trace("GET /api/v1/bots/news-item-data failed")
            return "", 400

        return news_item.NewsItemData.get_all_news_items_data(limit)


class BotsNode(Resource):
    @api_key_required
    def get(self, node_id):
        return bots_node.BotsNode.get_json_by_id(node_id)

    @api_key_required
    def put(self, node_id):
        return bots_manager.update_bots_node(node_id, request.json)

    @api_key_required
    def post(self):
        return bots_manager.add_bots_node(request.json)

    @api_key_required
    def delete(self, node_id):
        bots_node.BotsNode.delete(node_id)


class UpdateNewsItemAttributes(Resource):
    @api_key_required
    def put(self, news_item_data_id):
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class UpdateNewsItemTags(Resource):
    @api_key_required
    def put(self, news_item_data_id):
        news_item.NewsItemData.update_news_item_tags(news_item_data_id, request.json)


class GetNewsItemsAggregate(Resource):
    @api_key_required
    def get(self, group_id):

        resp_str = news_item.NewsItemAggregate.get_news_items_aggregate(group_id, request.json)
        return json.loads(resp_str)


class GetDefaultNewsItemsAggregate(Resource):
    @api_key_required
    def get(self):
        resp_str = news_item.NewsItemAggregate.get_default_news_items_aggregate(request.args.get("limit"))
        return json.loads(resp_str)


class WordListEntries(Resource):
    @api_key_required
    def delete(self, word_list_id, entry_name):
        return word_list.WordListEntry.delete_entries(word_list_id, entry_name)

    @api_key_required
    def put(self, word_list_id, entry_name):
        return word_list.WordListEntry.update_word_list_entries(word_list_id, entry_name, request.json)


class BotsStatusUpdate(Resource):
    @api_key_required
    def get(self, node_id):
        collector = bots_node.BotsNode.get_by_id(node_id)
        if not collector:
            return "", 404

        try:
            collector.updateLastSeen()
        except Exception as ex:
            logger.log_debug(ex)
            return {}, 400

        return {}, 200


def initialize(api):
    api.add_resource(NewsItemData, "/api/v1/bots/news-item-data")
    api.add_resource(
        UpdateNewsItemTags,
        "/api/v1/bots/news-item-data/<string:news_item_data_id>/tags",
    )
    api.add_resource(
        UpdateNewsItemAttributes,
        "/api/v1/bots/news-item-data/<string:news_item_data_id>/attributes",
    )
    api.add_resource(BotGroupAction, "/api/v1/bots/news-item-aggregates-group-action")
    api.add_resource(
        GetNewsItemsAggregate,
        "/api/v1/bots/news-item-aggregates-by-group/<string:group_id>",
    )
    api.add_resource(GetDefaultNewsItemsAggregate, "/api/v1/bots/news-item-aggregates")
    api.add_resource(
        WordListEntries,
        "/api/v1/bots/word-list/<int:word_list_id>/entries/<string:entry_name>",
    )
    api.add_resource(BotsNode, "/api/v1/bots/node/<string:node_id>", "/api/v1/bots/node")
    api.add_resource(BotsStatusUpdate, "/api/v1/bots/<string:node_id>")
