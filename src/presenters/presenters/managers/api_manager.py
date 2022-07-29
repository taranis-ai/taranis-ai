from flask_restful import Api
from presenters.api import isalive, presenters


def initialize(app):
    api = Api(app)

    isalive.initialize(api)
    presenters.initialize(api)
