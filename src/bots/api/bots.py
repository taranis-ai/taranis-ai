from flask_restful import Resource

from managers import bots_manager
from managers.auth_manager import api_key_required


class Bots(Resource):

    @api_key_required
    def get(self):
        return bots_manager.get_registered_bots_info()


def initialize(api):
    api.add_resource(Bots, "/api/v1/bots")
