from flask import Flask
from flask_cors import CORS
from presenters.managers import api_manager, presenters_manager, auth_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object("presenters.config.Config")

    with app.app_context():
        CORS(app)

        auth_manager.initialize(app)
        api_manager.initialize(app)
        presenters_manager.initialize()
    return app
