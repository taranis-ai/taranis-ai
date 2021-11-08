from flask import request
from flask_restful import Resource, reqparse

from managers import sse_manager, log_manager
from managers.auth_manager import api_key_required
from model import bot_preset, news_item, word_list


class BotPresetsForBots(Resource):

    @api_key_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("bot_type")
        parameters = parser.parse_args()
        return bot_preset.BotPreset.get_all_for_bot_json(parameters)


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
            limit = None
            if 'limit' in request.args and request.args['limit']:
                limit = request.args['limit']
        except Exception as ex:
            log_manager.debug_log(ex)
            return "", 400

        return news_item.NewsItemData.get_all_news_items_data(limit)


class UpdateNewsItemAttributes(Resource):

    @api_key_required
    def put(self, news_item_data_id):
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class GetNewsItemsAggregate(Resource):

    @api_key_required
    def get(self, group_id):
        return news_item.NewsItemAggregate.get_news_items_aggregate(group_id, request.json)


class Categories(Resource):

    @api_key_required
    def get(self, category_id):
        return word_list.WordListCategory.get_categories(category_id)

    @api_key_required
    def put(self, category_id):
        return word_list.WordList.add_word_list_category(category_id, request.json)


class Entries(Resource):

    @api_key_required
    def delete(self, category_id, entry_name):
        return word_list.WordListEntry.delete_entries(category_id, entry_name)

    @api_key_required
    def put(self, category_id, entry_name):
        return word_list.WordListEntry.update_word_list_entries(category_id, entry_name, request.json)


def initialize(api):
    api.add_resource(BotPresetsForBots, "/api/v1/bots/bots-presets")
    api.add_resource(NewsItemData, "/api/v1/bots/news-item-data")
    api.add_resource(UpdateNewsItemAttributes, "/api/v1/bots/news-item-data/<string:news_item_data_id>/attributes")
    api.add_resource(BotGroupAction, "/api/v1/bots/news-item-aggregates-group-action")
    api.add_resource(GetNewsItemsAggregate, "/api/v1/bots/news-item-aggregates-by-group/<string:group_id>")
    api.add_resource(Categories, "/api/v1/bots/word-list-categories/<int:category_id>")
    api.add_resource(Entries, "/api/v1/bots/word-list-categories/<int:category_id>/entries/<string:entry_name>")
