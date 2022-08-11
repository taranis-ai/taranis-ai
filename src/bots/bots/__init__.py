from flask import Flask
from flask_cors import CORS
import bots.managers as managers


def create_app():
    app = Flask(__name__)
    app.config.from_object("bots.config.Config")

    with app.app_context():
        CORS(app)

        managers.api_manager.initialize(app)
        managers.bots_manager.initialize()
    return app
