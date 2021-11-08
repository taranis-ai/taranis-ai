from flask_restful import Resource
from flask import request

from managers import collectors_manager
from managers.auth_manager import api_key_required
from managers.log_manager import log_debug


class Collectors(Resource):

    @api_key_required
    def post(self):
        log_debug("hello from core")
        if 'id' in request.json:
            log_debug("Got id for collector: {}".format(request.json['id']))
            return collectors_manager.get_registered_collectors_info(request.json['id'])
        return '', 400


class Collector(Resource):

    @api_key_required
    def put(self, collector_type):
        return collectors_manager.refresh_collector(collector_type)


def initialize(api):
    api.add_resource(Collectors, "/api/v1/collectors")
    api.add_resource(Collector, "/api/v1/collectors/<string:collector_type>")
