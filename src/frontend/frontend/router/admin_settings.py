from flask import Flask, Blueprint, request
from flask.views import MethodView

from frontend.auth import auth_required
from frontend.views.settings_views import SettingsView


class SettingsAPI(MethodView):
    @auth_required()
    def get(self):
        return SettingsView.static_view()


class SettingsAction(MethodView):
    @auth_required()
    def get(self, action: str):
        action_url = f"/admin/{action}?{request.query_string.decode()}"
        return SettingsView.settings_action(action_url)

    @auth_required()
    def post(self, action: str):
        action_url = f"/admin/{action}"
        return SettingsView.settings_action(action_url, method="post")


def init(app: Flask):
    settings_bp = Blueprint("admin_settings", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/admin/settings")

    settings_bp.add_url_rule("/", view_func=SettingsAPI.as_view("settings"))
    settings_bp.add_url_rule("/<path:action>", view_func=SettingsAction.as_view("settings_action"))

    app.register_blueprint(settings_bp)
