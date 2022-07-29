from flask import request
from flask_restful import Resource

from presenters.managers import presenters_manager
from presenters.managers.auth_manager import api_key_required


class Presenters(Resource):
    @api_key_required
    def get(self):
        return presenters_manager.get_registered_presenters_info()

    @api_key_required
    def post(self):
        return presenters_manager.generate(request.json)


def initialize(api):
    api.add_resource(Presenters, "/api/v1/presenters")
