import uuid
from flask import Flask, render_template, Blueprint, request, jsonify
from flask.views import MethodView
from flask_htmx import HTMX
from admin.filters import human_readable_trigger

from admin.core_api import CoreApi
from admin.config import Config


def is_htmx_request() -> bool:
    return "HX-Request" in request.headers


class Dashboard(MethodView):
    def get(self):
        result = CoreApi().get_dashboard()

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("index.html", data=result)

def init(app: Flask):
    HTMX(app)
    app.url_map.strict_slashes = False
    app.jinja_env.filters["human_readable"] = human_readable_trigger

    admin_bp = Blueprint("admin", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    admin_bp.add_url_rule("/", view_func=Dashboard.as_view("dashboard"))

    app.register_blueprint(admin_bp)
