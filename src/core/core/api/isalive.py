from flask import Flask
from flask.views import MethodView
from core.config import Config


class IsAlive(MethodView):
    def get(self):
        return {"isalive": True}


def initialize(app: Flask):
    base_url = f"{Config.APPLICATION_ROOT}api"
    app.add_url_rule(f"{base_url}/isalive", view_func=IsAlive.as_view("isalive"))
    app.add_url_rule(f"{base_url}/", view_func=IsAlive.as_view("isalive_"))
