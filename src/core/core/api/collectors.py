from flask import request
from flask_restful import Resource, reqparse

from core.managers import sse_manager, collectors_manager
from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.model import osint_source, news_item, collectors_node
from shared.schema.osint_source import OSINTSourceUpdateStatusSchema


class OSINTSourcesForCollectors(Resource):
    @api_key_required
    def get(self, collector_type):
        try:
            return osint_source.OSINTSource.get_all_by_type(collector_type)
        except Exception:
            logger.log_debug_trace()


class AddNewsItems(Resource):
    @api_key_required
    def post(self):
        json_data = request.json
        osint_source_ids = news_item.NewsItemAggregate.add_news_items(json_data)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class CollectorsNode(Resource):
    @api_key_required
    def get(self, node_id):
        return collectors_node.CollectorsNode.get_json_by_id(node_id)

    @api_key_required
    def put(self, node_id):
        return collectors_manager.update_collectors_node(node_id, request.json)

    @api_key_required
    def post(self):
        return collectors_manager.add_collectors_node(request.json)

    @api_key_required
    def delete(self, node_id):
        collectors_node.CollectorsNode.delete(node_id)


class OSINTSourceStatusUpdate(Resource):
    @api_key_required
    def put(self, osint_source_id):
        source = osint_source.OSINTSource.get_by_id(osint_source_id)
        if not source:
            return {}, 404

        try:
            osint_source_status = OSINTSourceUpdateStatusSchema().load(request.json)
            logger.debug(f"osint_source_status: ${osint_source_status}")
        except Exception:
            logger.log_debug_trace()
            return {}, 400

        return {}, 200


def initialize(api):
    api.add_resource(
        OSINTSourcesForCollectors,
        "/api/v1/collectors/osint-sources/<string:collector_type>",
    )
    api.add_resource(
        OSINTSourceStatusUpdate,
        "/api/v1/collectors/osint-sources/<string:osint_source_id>",
    )
    api.add_resource(AddNewsItems, "/api/v1/collectors/news-items")
    api.add_resource(CollectorsNode, "/api/v1/collectors/node/<string:node_id>", "/api/v1/collectors/node")
