from flask import request
from flask_restful import Resource, reqparse

from managers import sse_manager
from managers.auth_manager import api_key_required
from managers.log_manager import log_debug
from model import osint_source, collectors_node, news_item
from schema.osint_source import OSINTSourceUpdateStatusSchema


class OSINTSourcesForCollectors(Resource):

    @api_key_required
    def get(self, collector_id):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("collector_type")
        parameters = parser.parse_args()

        node = collectors_node.CollectorsNode.get_by_id(collector_id)
        if not node:
            return '', 404

        node.updateLastSeen()

        return osint_source.OSINTSource.get_all_for_collector_json(node, parameters.collector_type)


class AddNewsItems(Resource):

    @api_key_required
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_items(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)

class OSINTSourceStatusUpdate(Resource):
    @api_key_required
    def put(self, osint_source_id):
        source = osint_source.OSINTSource.get_by_id(osint_source_id)
        if not source:
            return {}, 404

        try:
            osint_source_status_schema = OSINTSourceUpdateStatusSchema()
            osint_source_status = osint_source_status_schema.load(request.json)
        except Exception as ex:
            log_debug(ex)
            return {}, 400

        return {}, 200

class CollectorStatusUpdate(Resource):
    @api_key_required
    def get(self, collector_id):
        collector = collectors_node.CollectorsNode.get_by_id(collector_id)
        if not collector:
            return '', 404

        try:
            collector.updateLastSeen()
        except Exception as ex:
            log_debug(ex)
            return {}, 400

        return {}, 200

def initialize(api):
    api.add_resource(OSINTSourcesForCollectors, "/api/v1/collectors/<string:collector_id>/osint-sources")
    api.add_resource(OSINTSourceStatusUpdate, "/api/v1/collectors/osint-sources/<string:osint_source_id>")
    api.add_resource(CollectorStatusUpdate, "/api/v1/collectors/<string:collector_id>")
    api.add_resource(AddNewsItems, "/api/v1/collectors/news-items")
