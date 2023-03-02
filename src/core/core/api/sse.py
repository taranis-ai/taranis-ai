from flask_restful import Resource
from flask import request
from flask_jwt_extended import jwt_required

from core.managers.sse_manager import sse_manager


class SSE(Resource):
    @jwt_required()
    def get(self):
        return sse_manager.sse.listeners


def initialize(api):
    api.add_resource(SSE, "/sse")
