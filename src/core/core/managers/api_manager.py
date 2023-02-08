from flask_restful import Api
from core.config import Config
from swagger_ui import api_doc
import os

import core.api as core_api


def initialize(app):
    api = Api(app)

    openapi_yaml = os.path.join("core", Config.OpenAPI, "openapi3_0.yaml")
    api_doc(app, config_path=openapi_yaml, url_prefix="/api/v1/doc", editor=False)

    core_api.analyze.initialize(api)
    core_api.assess.initialize(api)
    core_api.assets.initialize(api)
    core_api.auth.initialize(api)
    core_api.bots.initialize(api)
    core_api.collectors.initialize(api)
    core_api.config.initialize(api)
    core_api.dashboard.initialize(api)
    core_api.isalive.initialize(api)
    core_api.publish.initialize(api)
    core_api.user.initialize(api)
    core_api.remote.initialize(api)
