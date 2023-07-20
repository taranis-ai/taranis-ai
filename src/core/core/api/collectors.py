from flask import request
from flask_restx import Resource, Namespace

from core.managers.sse_manager import sse_manager
from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.model import osint_source, news_item


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
        result, status = news_item.NewsItemAggregate.add_news_items(json_data)
        sse_manager.news_items_updated()
        return result, status


class OSINTSourceStatusUpdate(Resource):
    @api_key_required
    def put(self, osint_source_id):
        try:
            source = osint_source.OSINTSource.get(osint_source_id)
            if not source:
                return {"error": f"OSINTSource with ID: {osint_source_id} not found"}, 404

            if request_json := request.json:
                source.update_status(request_json.get("error", None))
            return {"message": "Status updated"}
        except Exception:
            logger.log_debug_trace()
            return {"error": "Could not update status"}, 500


def initialize(api):
    namespace = Namespace("Collectors", description="Collectors related operations", path="/api/v1/collectors")
    namespace.add_resource(
        OSINTSourcesForCollectors,
        "/osint-sources/<string:collector_type>",
    )
    namespace.add_resource(
        OSINTSourceStatusUpdate,
        "/osint-source/<string:osint_source_id>",
    )

    namespace.add_resource(AddNewsItems, "/news-items")
    api.add_namespace(namespace)
