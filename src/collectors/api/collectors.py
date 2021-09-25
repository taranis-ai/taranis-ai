from flask_restful import Resource
from managers import collectors_manager
from managers.auth_manager import api_key_required


class Collectors(Resource):

    @api_key_required
    def get(self):
        return collectors_manager.get_registered_collectors_info()


def initialize(api):
    api.add_resource(Collectors, "/api/v1/collectors")
