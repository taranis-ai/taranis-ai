from flask_restx import Resource, Namespace

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
    namespace = Namespace("Collectors", description="Collectors related operations", path="/api/v1/collectors")
    namespace.add_resource(Collectors, "/")
    namespace.add_resource(Collector, "/<string:collector_type>")
    api.add_namespace(namespace)
