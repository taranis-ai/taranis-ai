from flask_restx import Resource, reqparse, Namespace
from flask import request

from core.managers.auth_manager import auth_required, api_key_required
from core.model import publisher_preset


class PublisherPresets(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher_preset.PublisherPreset.get_all_json(search)

    @api_key_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("collector_type")
        parameters = parser.parse_args()
        return publisher_preset.PublisherPreset.get_all_for_publisher_json(parameters)


class PublisherPreset(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        pub_result = publisher_preset.PublisherPreset.add(request.json)
        return {"id": pub_result.id, "message": "Publisher preset created successfully"}, 200

    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, id):
        pub_result = publisher_preset.PublisherPreset.update(id, request.json)
        if not pub_result:
            return {"message": "Publisher preset not found"}, 404
        return {"id": pub_result, "message": "Publisher preset updated successfully"}, 200

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, id):
        return publisher_preset.PublisherPreset.delete(id)


def initialize(api):
    namespace = Namespace("publishers", description="Publishers API", path="/api/v1/publishers")
    namespace.add_resource(PublisherPresets, "/presets")
    namespace.add_resource(PublisherPreset, "/preset", "/preset/<id>")
    api.add_namespace(namespace)
