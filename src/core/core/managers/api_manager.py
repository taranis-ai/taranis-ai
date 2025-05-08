from flask import jsonify
from flask_cors import CORS

import core.api as core_api
from core.log import logger


def initialize(app):
    CORS(app)

    app.url_map.strict_slashes = False
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(401, handle_unauthorized)
    app.register_error_handler(404, handle_not_found)

    core_api.admin.initialize(app)
    core_api.analyze.initialize(app)
    core_api.assess.initialize(app)
    core_api.assets.initialize(app)
    core_api.auth.initialize(app)
    core_api.bots.initialize(app)
    core_api.config.initialize(app)
    core_api.connectors.initialize(app)
    core_api.dashboard.initialize(app)
    core_api.isalive.initialize(app)
    core_api.publish.initialize(app)
    core_api.user.initialize(app)
    core_api.task.initialize(app)
    core_api.worker.initialize(app)
    core_api.static.initialize(app)


def handle_bad_request(e):
    if hasattr(e, "description"):
        return jsonify(error=str(e.description)), 400
    return jsonify(error="Bad request"), 400


def handle_unauthorized(e):
    if hasattr(e, "description"):
        return jsonify(error=str(e.description)), 401
    return jsonify(error="Unauthorized"), 401


def handle_not_found(e):
    logger.debug(f"404 not found: {e}")
    if hasattr(e, "item"):
        return jsonify(error=f"{e.item} not found"), 404
    return jsonify(error="Not found"), 404
