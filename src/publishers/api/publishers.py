from flask_restful import Resource
from flask import request

from managers import publishers_manager
from managers.auth_manager import api_key_required


class Publishers(Resource):

    @api_key_required
    def get(self):
        return publishers_manager.get_registered_publishers_info()

    @api_key_required
    def post(self):
        publishers_manager.publish(request.json)


def initialize(api):
    api.add_resource(Publishers, "/api/v1/publishers")
