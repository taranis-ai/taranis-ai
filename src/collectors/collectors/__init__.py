from flask import Flask
from flask_cors import CORS

from collectors.managers import api_manager, collectors_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object("collectors.config.Config")

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        collectors_manager.initialize()

    return app
