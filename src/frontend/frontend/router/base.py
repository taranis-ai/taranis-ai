from flask import Flask, render_template, Blueprint, request, Response, jsonify, url_for
from flask.views import MethodView
from flask_jwt_extended import set_access_cookies

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache import get_cached_users, list_cache_keys
from models.admin import Dashboard
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
    def get(self, suffix: str | None = None):
        if not suffix:
            DataPersistenceLayer().invalidate_cache(None)
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
        if CoreApi().check_if_api_connected():
            return render_template("login/index.html")
        return render_template("login/index.html", error=f"API is not reachable - {Config.TARANIS_CORE_URL}"), 500

    def post(self):
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("login/index.html", login_error="Username and password are required"), 400

        core_response = CoreApi().login(username, password)

        jwt_token = core_response.json().get("access_token")

        logger.debug(f"Login response: {jwt_token}")

        if not core_response.ok:
            return render_template("login/index.html", login_error=core_response.json().get("error")), core_response.status_code

        response = Response(status=302, headers={"Location": url_for("base.dashboard")})
        set_access_cookies(response, jwt_token)

        return response

    def delete(self):
        core_response = CoreApi().logout()
        if not core_response.ok:
            return render_template("login/index.html", login_error=core_response.json().get("error")), core_response.status_code

        response = Response(status=200, headers={"HX-Redirect": url_for("base.login")})
        response.delete_cookie("access_token")
        return response


def init(app: Flask):
    base_bp = Blueprint("base", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    base_bp.add_url_rule("/", view_func=DashboardAPI.as_view("dashboard"))
    base_bp.add_url_rule("/dashboard", view_func=DashboardAPI.as_view("dashboard_"))

    base_bp.add_url_rule("/login", view_func=LoginView.as_view("login"))
    base_bp.add_url_rule("/logout", view_func=LoginView.as_view("logout"))

    base_bp.add_url_rule("/invalidate_cache", view_func=InvalidateCache.as_view("invalidate_cache"))
    base_bp.add_url_rule("/invalidate_cache/<string:suffix>", view_func=InvalidateCache.as_view("invalidate_cache_suffix"))
    base_bp.add_url_rule("/list_cache_keys", view_func=ListCacheKeys.as_view("list_cache_keys"))
    base_bp.add_url_rule("/list_user_cache", view_func=ListUserCache.as_view("list_user_cache"))

    app.register_blueprint(base_bp)
