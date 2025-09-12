from flask import Flask

from core.managers import db_manager, auth_manager, api_manager, data_manager, sentry_manager
from core.config import Config


def granian_app() -> Flask:
    return create_app(False, False)


def create_app(initial_setup: bool = True, db_setup: bool = False) -> Flask:
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}static")
    app.config.from_object("core.config.Config")

    with app.app_context():
        if db_setup:
            initilize_database(app)
            return app
        initialize_managers(app, initial_setup)

    return app


def initilize_database(app: Flask):
    db_manager.initialize(app, True)
    data_manager.initialize(True)


def initialize_managers(app: Flask, initial_setup: bool = True):
    sentry_manager.initialize()
    db_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    data_manager.initialize(initial_setup)
