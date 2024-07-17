import os
import sentry_sdk

from flask import Flask
from dotenv import load_dotenv

from core.managers import (
    db_manager,
    auth_manager,
    api_manager,
    queue_manager,
    data_manager,
)


def create_app(initial_setup: bool = True):
    sentry_init()
    app = Flask(__name__)
    app.config.from_object("core.config.Config")

    with app.app_context():
        initialize_managers(app, initial_setup)

    return app


def sentry_init():
    load_dotenv()
    sentry_sdk.init(
        dsn = os.getenv("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", 1.0)),
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", 1.0))
    )


def initialize_managers(app: Flask, initial_setup: bool = False):
    db_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    queue_manager.initialize(app, initial_setup)
    data_manager.initialize(initial_setup)
