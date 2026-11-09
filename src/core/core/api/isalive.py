from flask import Flask, current_app
from flask.views import MethodView
from models.dashboard import CoreStatus

from core.config import Config


class IsAlive(MethodView):
    def get(self):
        return CoreStatus(isalive=True, debug=current_app.debug).model_dump()


def initialize(app: Flask):
    base_url = f"{Config.APPLICATION_ROOT}api"
    app.add_url_rule(f"{base_url}/isalive", view_func=IsAlive.as_view("isalive"))
    app.add_url_rule(f"{base_url}/", view_func=IsAlive.as_view("isalive_"))
