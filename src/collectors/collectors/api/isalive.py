from flask_restful import Resource


class IsAlive(Resource):
    def get(self):
        return {"isalive": True}


def initialize(api):
    api.add_resource(IsAlive, "/api/v1/isalive")
