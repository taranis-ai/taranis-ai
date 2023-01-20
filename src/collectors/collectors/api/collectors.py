from flask_restful import Resource

from collectors.managers import collectors_manager
from collectors.managers.auth_manager import api_key_required


class Collectors(Resource):
    @api_key_required
    def get(self):
        return collectors_manager.get_registered_collectors_info()

    @api_key_required
    def post(self):
        return collectors_manager.refresh()


class Collector(Resource):
    @api_key_required
    def put(self, collector_type: str):
        return collectors_manager.refresh_collector(collector_type)

    @api_key_required
    def post(self, collector_type: str):
        return collectors_manager.refresh_collector(collector_type)


def initialize(api):
    api.add_resource(Collectors, "/api/v1/collectors")
    api.add_resource(Collector, "/api/v1/collectors/<string:collector_type>")
