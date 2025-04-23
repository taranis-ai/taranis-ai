from flask import Flask
from frontend import router
from frontend.config import Config
from frontend import auth
from frontend import cache
from frontend import setup


def create_app():
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}/static")
    app.config.from_object("frontend.config.Config")

    with app.app_context():
        init(app)

    return app


def init(app: Flask):
    cache.init(app)
    auth.init(app)
    setup.init(app)
    router.init(app)
