from flask_restful import Resource

from bots.managers.bots_manager import get_registered_bots_info, refresh
from bots.managers.auth_manager import api_key_required


class Bots(Resource):
    @api_key_required
    def get(self):
        return get_registered_bots_info()

    @api_key_required
    def post(self):
        return refresh()


def initialize(api):
    api.add_resource(Bots, "/api/v1/bots")
