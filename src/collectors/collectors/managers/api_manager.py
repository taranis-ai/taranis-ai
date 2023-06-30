from flask_restx import Api

from collectors.api import isalive, collectors


def initialize(app):
    api = Api(app)

    isalive.initialize(api)
    collectors.initialize(api)
