from flask import Flask

from frontend import auth, cache, router, setup
from frontend.config import Config


def create_app():
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}/static")
    app.config.from_object("frontend.config.Config")
    app.secret_key = Config.FLASK_SECRET_KEY.get_secret_value()

    with app.app_context():
        init(app)

    return app


def init(app: Flask):
    cache.init(app)
    auth.init(app)
    setup.init(app)
    router.init(app)
