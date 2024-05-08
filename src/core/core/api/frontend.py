import os

from flask import Flask, send_from_directory
from flask.views import MethodView
from core.log import logger


class Frontend(MethodView):
    def get(self, filename="index.html"):
        try:
            return send_from_directory("../../gui/dist", filename)
        except Exception as e:
            logger.warning(f"Error: {e}")
            return os.listdir(".")


def initialize(app: Flask):
    logger.info("Initializing frontend for e2e tests")
    app.add_url_rule("/<path:filename>", view_func=Frontend.as_view("frontend"))
    app.add_url_rule("/", view_func=Frontend.as_view("frontend_"))
