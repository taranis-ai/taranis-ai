from flask import Flask
from flask_cors import CORS

from managers import api_manager, publishers_manager


def create_app():
    app = Flask(__name__)

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        publishers_manager.initialize()

    return app
