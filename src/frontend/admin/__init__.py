from flask import Flask
from admin import router
from admin.config import Config


def create_app():
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}/static")
    app.config.from_object("admin.config.Config")

    with app.app_context():
        init(app)

    return app


def init(app: Flask):
    router.init(app)
