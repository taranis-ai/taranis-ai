from flask import Flask
from asgiref.wsgi import WsgiToAsgi


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


def create_asgi_app(initial_setup: bool = True):
    app = create_app(initial_setup)
    return WsgiToAsgi(app)


def initialize_managers(app: Flask, initial_setup: bool = False):
    db_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    queue_manager.initialize(app, initial_setup)
    data_manager.initialize(initial_setup)
