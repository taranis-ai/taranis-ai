from flask import Flask
from flask_cors import CORS

from managers import *
from model import *  # just until all new model classes are used regularly


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    with app.app_context():
        CORS(app)

        db_manager.initialize(app)
        db_manager.create_tables()

        auth_manager.initialize(app)
        api_manager.initialize(app)

        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)

        # import test

    return app
