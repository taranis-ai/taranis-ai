from flask import Flask
from flask.views import MethodView

from core.config import Config
from core.service import health as health_service


class Health(MethodView):
    def get(self):
        return health_service.get_health_response()


def initialize(app: Flask):
    base_url = f"{Config.APPLICATION_ROOT}api"
    app.add_url_rule(f"{base_url}/health", view_func=Health.as_view("health"))
