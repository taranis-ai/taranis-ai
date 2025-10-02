from flask import Flask, Blueprint

from frontend.views.user_views import UserProfileView


def init(app: Flask):
    user_bp = Blueprint("user", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    user_bp.add_url_rule("/profile", view_func=UserProfileView.as_view("profile"))
    user_bp.add_url_rule("/settings", view_func=UserProfileView.get_settings_view, methods=["GET"], endpoint="settings")

    app.register_blueprint(user_bp)
