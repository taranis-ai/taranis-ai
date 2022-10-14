from flask_restful import Api

import core.api as core_api


def initialize(app):
    api = Api(app)

    core_api.assess.initialize(api)
    core_api.auth.initialize(api)
    core_api.collectors.initialize(api)
    core_api.isalive.initialize(api)
    core_api.openapi.initialize(api)
    core_api.config.initialize(api)
    core_api.analyze.initialize(api)
    core_api.publish.initialize(api)
    core_api.user.initialize(api)
    core_api.assets.initialize(api)
    core_api.bots.initialize(api)
    core_api.remote.initialize(api)
    core_api.dashboard.initialize(api)
