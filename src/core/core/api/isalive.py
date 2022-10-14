from flask_restful import Resource

from core.managers.auth_manager import no_auth


class IsAlive(Resource):
    @no_auth
    def get(self):
        return {"isalive": True}


def initialize(api):
    api.add_resource(IsAlive, "/api/v1/isalive", "/")
