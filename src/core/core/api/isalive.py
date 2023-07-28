from flask_restx import Resource, Api

from core.managers.auth_manager import no_auth


class IsAlive(Resource):
    @no_auth
    def get(self):
        return {"isalive": True}


def initialize(api: Api):
    api.add_resource(IsAlive, "/api/v1/isalive", "/")
