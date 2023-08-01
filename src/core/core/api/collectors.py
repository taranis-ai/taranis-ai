from flask import request
from flask_restx import Resource, Namespace, Api

from core.managers.sse_manager import sse_manager
from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.model import osint_source, news_item


class AddNewsItems(Resource):
    @api_key_required
    def post(self):
        json_data = request.json
        result, status = news_item.NewsItemAggregate.add_news_items(json_data)
        sse_manager.news_items_updated()
        return result, status


def initialize(api: Api):
    namespace = Namespace("Collectors", description="Collectors related operations", path="/api/v1/collectors")

    namespace.add_resource(AddNewsItems, "/news-items")
    api.add_namespace(namespace)
