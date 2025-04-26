from flask import Flask

from frontend.views.base_view import BaseView


def init(app: Flask):
    app.jinja_env.globals["views"] = BaseView._registry
