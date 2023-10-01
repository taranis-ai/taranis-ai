from flask_restx import Api
from swagger_ui import api_doc
from flask import jsonify
from pathlib import Path

import core.api as core_api


def initialize(app):
    api = Api(app, version="1", title="Taranis NG API", doc="/api/swagger", prefix="/api")

    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(401, handle_unauthorized)
    app.register_error_handler(404, handle_not_found)

    openapi_yaml = Path(__file__).parent.parent / "static" / "openapi3_0.yaml"
    api_doc(app, config_path=openapi_yaml, url_prefix="/api/doc", editor=False)

    core_api.analyze.initialize(api)
    core_api.assess.initialize(api)
    core_api.assets.initialize(api)
    core_api.auth.initialize(api)
    core_api.bots.initialize(api)
    core_api.config.initialize(api)
    core_api.dashboard.initialize(api)
    core_api.isalive.initialize(api)
    core_api.publish.initialize(api)
    core_api.user.initialize(api)
    core_api.worker.initialize(api)


def handle_bad_request(e):
    if hasattr(e, "description"):
        return jsonify(error=str(e.description)), 400
    return jsonify(error="Bad request"), 400


def handle_unauthorized(e):
    if hasattr(e, "description"):
        return jsonify(error=str(e.description)), 401
    return jsonify(error="Unauthorized"), 401


def handle_not_found(e):
    if hasattr(e, "item"):
        return jsonify(error=f"{e.item} not found"), 404
    return jsonify(error="Not found"), 404
