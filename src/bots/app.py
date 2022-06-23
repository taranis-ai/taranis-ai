from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

import managers


def create_app():
    app = Flask(__name__)
    load_dotenv()

    with app.app_context():
        CORS(app)

        managers.api_manager.initialize(app)
        managers.bots_manager.initialize()
        managers.sse_manager.initialize()

    return app
