from flask import Flask
from flask_cors import CORS

from managers import (
    db_manager,
    auth_manager,
    api_manager,
    sse_manager,
    remote_manager,
    tagcloud_manager,
    log_manager,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    with app.app_context():
        CORS(app)

        db_manager.initialize(app)
        log_manager.logger.log_info("DB Done")

        auth_manager.initialize(app)
        api_manager.initialize(app)

        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)
        log_manager.logger.log_info("All Done")
        # import test

    return app
