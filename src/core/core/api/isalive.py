from flask import Flask
from flask.views import MethodView
from core.managers.auth_manager import no_auth


class IsAlive(MethodView):
    @no_auth
    def get(self):
        return {"isalive": True}


def initialize(app: Flask):
    app.add_url_rule("/api/isalive", view_func=IsAlive.as_view("isalive"))
    app.add_url_rule("/api/", view_func=IsAlive.as_view("isalive_"))
