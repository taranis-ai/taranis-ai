from flask import Flask
from flask.views import MethodView

from core.config import Config
from core.service import health as health_service


class Health(MethodView):
    def get(self):
        return health_service.get_health_response()


def readiness():
    ready = health_service.check_seed_data() == "up" and (not Config.QUEUE_ENABLED or health_service.check_broker() == "up")
    return {"ready": ready}, 200 if ready else 503


def initialize(app: Flask):
    base_url = f"{Config.APPLICATION_ROOT}api"
    app.add_url_rule(f"{base_url}/health", view_func=Health.as_view("health"))
    app.add_url_rule(f"{base_url}/ready", view_func=readiness)
