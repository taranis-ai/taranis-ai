from pathlib import Path

import yaml
from flask import Flask
from flask_openapi import OpenAPI
from models.task import TaskErrorResponse

from core.api.task import task_validation_error
from core.config import Config
from core.managers import api_manager, auth_manager, db_manager, queue_manager, telemetry_manager
from core.security import init_app as init_security


def granian_app() -> Flask:
    return create_app(False, False)


def create_app(initial_setup: bool = True, db_setup: bool = False) -> OpenAPI:
    app = OpenAPI(
        __name__,
        static_url_path=f"{Config.APPLICATION_ROOT}static",
        doc_ui=False,
        validation_error_status=400,
        validation_error_model=TaskErrorResponse,
        validation_error_callback=task_validation_error,
    )
    app.config.from_object("core.config.Config")
    init_security(app)

    with app.app_context():
        if db_setup:
            initilize_database(app)
            return app
        initialize_managers(app, initial_setup)

    with (Path(__file__).parent / "static/openapi3_1.yaml").open(encoding="utf-8") as stream:
        legacy_spec = yaml.safe_load(stream)
    generated_spec = app.api_doc
    api_prefix = f"{Config.APPLICATION_ROOT}api"
    legacy_spec["paths"].update({path.removeprefix(api_prefix): path_item for path, path_item in generated_spec["paths"].items()})
    legacy_spec["components"]["schemas"].update(generated_spec["components"]["schemas"])
    app.spec_json = legacy_spec

    return app


def initilize_database(app: Flask):
    db_manager.initialize(app, True)
    queue_manager.initialize(app, True)


def initialize_managers(app: Flask, initial_setup: bool = True):
    telemetry_manager.initialize(app)
    db_manager.initialize(app, initial_setup)
    queue_manager.initialize(app, initial_setup)
    auth_manager.initialize(app)
    api_manager.initialize(app)
