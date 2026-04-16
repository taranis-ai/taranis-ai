from flask import Blueprint, Flask, request
from flask.views import MethodView

from frontend.auth import admin_required
from frontend.views.admin_views.settings_views import SettingsView


class SettingsAction(MethodView):
    @admin_required()
    def get(self, action: str):
        action_path = action.replace("_", "-")
        query_string = request.query_string.decode()
        action_url = f"/settings/{action_path}"
        if query_string:
            action_url = f"{action_url}?{query_string}"
        return SettingsView.settings_action(action_url)

    @admin_required()
    def post(self, action: str):
        action_url = f"/settings/{action.replace('_', '-')}"
        return SettingsView.settings_action(action_url, method="post")


def init(app: Flask):
    settings_bp = Blueprint("admin_settings", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/admin/settings")

    settings_bp.add_url_rule("/", view_func=SettingsView.as_view("settings"))
    settings_bp.add_url_rule("/<path:action>", view_func=SettingsAction.as_view("settings_action"))

    app.register_blueprint(settings_bp)
