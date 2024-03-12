from flask_restx import Resource, Api
from flask_jwt_extended import jwt_required
from flask import Response, stream_with_context
from core.managers.sse_manager import sse_manager


class SSE(Resource):
    @jwt_required()
    def get(self):
        def stream():
            messages = sse_manager.sse.listen()
            while True:
                msg = messages.get()
                yield msg

        return Response(stream_with_context(stream()), mimetype="text/event-stream")


def initialize(api: Api):
    api.add_resource(SSE, "/sse")
