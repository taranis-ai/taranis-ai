import os
import contextlib
from flask import Flask
from flask_cors import CORS
from core.managers import (
    db_manager,
    auth_manager,
    api_manager,
    log_manager,
    queue_manager,
    data_manager,
)

FLAG_FILENAME = "worker_init.flag"
FIRST_WORKER = "gunicorn" not in os.environ.get("SERVER_SOFTWARE", "")


def create_app():
    app = Flask(__name__)
    app.config.from_object("core.config.Config")

    with app.app_context():
        initialize_managers(app)

    return app


def initialize_managers(app):
    global FIRST_WORKER
    CORS(app)

    if FIRST_WORKER:
        log_manager.logger.info(f"Connecting Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    db_manager.initialize(app, FIRST_WORKER)
    auth_manager.initialize(app)
    api_manager.initialize(app)
    queue_manager.initialize(app, FIRST_WORKER)
    data_manager.initialize(FIRST_WORKER)

    if FIRST_WORKER:
        log_manager.logger.info("All Managers initialized")


def post_fork(server, worker):
    global FIRST_WORKER
    if not create_flag_file():
        FIRST_WORKER = False
        return
    FIRST_WORKER = True
    log_manager.logger.debug(f"Worker {worker.pid} is the first worker and will perform the one-time tasks.")


def on_starting_and_exit(server):
    with contextlib.suppress(FileNotFoundError):
        os.remove(FLAG_FILENAME)


def create_flag_file():
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        file_descriptor = os.open(FLAG_FILENAME, flags)
        os.close(file_descriptor)
        return True
    except FileExistsError:
        return False
