from flask import Flask
from flask_cors import CORS
from dotenv import dotenv_values
from publishers.managers import api_manager, publishers_manager, auth_manager


def create_app(dotenv_path="."):
    app = Flask(__name__)
    app.config.from_object("publishers.config.Config")
    app.config.from_mapping(dotenv_values(dotenv_path=dotenv_path))

    with app.app_context():
        CORS(app)

        auth_manager.initialize(app)
        api_manager.initialize(app)
        publishers_manager.initialize()
    return app


app = create_app()
