from typing import Any

from flask import Flask

from frontend import auth, cache, core_api, router, setup
from frontend.config import Config, build_config_overrides
from frontend.security import init_app as init_security


def create_app(config_overrides: dict[str, Any] | None = None):
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}/static")
    app.config.from_object("frontend.config.Config")
    app.config.update(build_config_overrides(config_overrides))
    init_security(app)
    app.secret_key = Config.FLASK_SECRET_KEY.get_secret_value()

    with app.app_context():
        init(app)

    return app


def init(app: Flask):
    core_api.init_app(app)
    cache.init(app)
    auth.init(app)
    setup.init(app)
    router.init(app)
