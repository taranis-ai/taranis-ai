import os

from flask import Flask, send_from_directory
from flask.views import MethodView


class Frontend(MethodView):
    def get(self, filename="index.html"):
        try:
            return send_from_directory("../../gui/dist", filename)
        except Exception as e:
            print(e)
            return os.listdir(".")


def initialize(app: Flask):
    app.add_url_rule("/<path:filename>", view_func=Frontend.as_view("frontend"))
    app.add_url_rule("/", view_func=Frontend.as_view("frontend_"))
