from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from managers import *


def create_app():
    app = Flask(__name__)
    load_dotenv()

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        bots_manager.initialize()
        sse_manager.initialize()

    return app
