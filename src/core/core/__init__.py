from flask import Flask

from core.managers import (
    db_manager,
    auth_manager,
    api_manager,
    queue_manager,
    data_manager,
)


def create_app(initial_setup: bool = True):
    app = Flask(__name__)
    app.config.from_object("core.config.Config")

    with app.app_context():
        initialize_managers(app, initial_setup)

    return app


def initialize_managers(app: Flask, initial_setup: bool = False):
    1/0
    db_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    queue_manager.initialize(app, initial_setup)
    data_manager.initialize(initial_setup)
