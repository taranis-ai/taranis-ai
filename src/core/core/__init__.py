from flask import Flask
from typing import Literal

from core.managers import db_manager, auth_manager, api_manager, queue_manager, data_manager, sentry_manager, schedule_manager
from core.config import Config


def create_app(startup_mode: Literal["db_setup", "single_worker", "multi_worker"] = "single_worker") -> Flask:
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}static")
    app.config.from_object("core.config.Config")

    with app.app_context():
        if startup_mode == "db_setup":
            initilize_database(app)
            return app
        initial_setup = startup_mode == "single_worker"
        initialize_managers(app, initial_setup=initial_setup)

    return app


def initilize_database(app: Flask):
    db_manager.initialize(app, True)
    data_manager.initialize(True)
    schedule_manager.Scheduler()


def initialize_managers(app: Flask, initial_setup: bool = True):
    sentry_manager.initialize()
    db_manager.initialize(app, initial_setup)
    queue_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    data_manager.initialize(initial_setup)
    schedule_manager.initialize()
    queue_manager.queue_manager.post_init()
