from flask_restful import Resource
from flask import request

from collectors.managers import collectors_manager
from collectors.managers.auth_manager import api_key_required
from collectors.managers.log_manager import logger


class Collectors(Resource):
    @api_key_required
    def post(self):
        if "id" in request.json:
            logger.log_debug(f'Got id for collector: {request.json["id"]}')
            collectors_manager.update_collector_id(request.json["id"])
            return collectors_manager.get_registered_collectors_info()
        return "", 400

    @api_key_required
    def get(self):
        return collectors_manager.get_registered_collectors_info()


class Collector(Resource):
    @api_key_required
    def put(self, collector_type):
        return collectors_manager.refresh_collector(collector_type)


def initialize(api):
    api.add_resource(Collectors, "/api/v1/collectors")
    api.add_resource(Collector, "/api/v1/collectors/<string:collector_type>")
