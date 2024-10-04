from flask import Flask

from core.managers import db_manager, auth_manager, api_manager, queue_manager, data_manager, sentry_manager, schedule_manager
from core.config import Config


def create_app(initial_setup: bool = True):
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}static")
    app.config.from_object("core.config.Config")

    with app.app_context():
        initialize_managers(app, initial_setup)

    return app


def initialize_managers(app: Flask, initial_setup: bool = False):
    sentry_manager.initialize()
    db_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    queue_manager.initialize(app, initial_setup)
    data_manager.initialize(initial_setup)
    schedule_manager.initialize()
