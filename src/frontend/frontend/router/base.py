from flask import Flask, render_template, Blueprint, request, Response, jsonify
from flask.views import MethodView
from flask_jwt_extended import set_access_cookies

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache import get_cached_users, list_cache_keys
from frontend.models import Dashboard
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required


class DashboardAPI(MethodView):
    @auth_required()
    def get(self):
        result = DataPersistenceLayer().get_objects(Dashboard)

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("dashboard/index.html", data=result[0])


class InvalidateCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self, suffix: str):
        if not suffix:
            return {"error": "No suffix provided"}, 400
        DataPersistenceLayer().invalidate_cache(suffix)
        return "Cache invalidated"


class ListCacheKeys(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return Response("<br>".join(list_cache_keys()))


class ListUserCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return jsonify(get_cached_users())


class LoginView(MethodView):
    def get(self):
        return render_template("login/index.html")

    def post(self):
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("login/index.html", error="Username and password are required"), 400

        core_response = CoreApi().login(username, password)

        jwt_token = core_response.json().get("access_token")

        logger.debug(f"Login response: {jwt_token}")

        if not core_response.ok:
            return render_template("login/index.html", error=core_response.json().get("error")), core_response.status_code

        response = Response(status=core_response.status_code, headers={"HX-Redirect": "/frontend/"})
        set_access_cookies(response, jwt_token)

        return response


def init(app: Flask):
    base_bp = Blueprint("base", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    base_bp.add_url_rule("/", view_func=DashboardAPI.as_view("dashboard"))

    base_bp.add_url_rule("/login", view_func=LoginView.as_view("login"))

    base_bp.add_url_rule("/invalidate_cache/<suffix>", view_func=InvalidateCache.as_view("invalidate_cache"))
    base_bp.add_url_rule("/list_cache_keys", view_func=ListCacheKeys.as_view("list_cache_keys"))
    base_bp.add_url_rule("/list_user_cache", view_func=ListUserCache.as_view("list_user_cache"))

    app.register_blueprint(base_bp)
