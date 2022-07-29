from flask_restful import Api

from publishers.api import isalive, publishers


def initialize(app):
    api = Api(app)

    isalive.initialize(api)
    publishers.initialize(api)
