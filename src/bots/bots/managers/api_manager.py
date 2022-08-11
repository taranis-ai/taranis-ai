from flask_restful import Api

import bots.api as apis


def initialize(app):
    api = Api(app)

    apis.isalive.initialize(api)
    apis.bots.initialize(api)
