from flask import Blueprint, Flask

from frontend.views.user_views import UserNotificationView, UserProfileView, UserTaskView


def init(app: Flask):
    user_bp = Blueprint("user", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    user_bp.add_url_rule("/profile", view_func=UserProfileView.as_view("profile"))
    user_bp.add_url_rule("/tasks", view_func=UserTaskView.as_view("tasks"))
    user_bp.add_url_rule("/notifications", view_func=UserNotificationView.as_view("notifications"))
    user_bp.add_url_rule("/settings", view_func=UserProfileView.get_settings_view, methods=["GET"], endpoint="settings")
    user_bp.add_url_rule("/settings", view_func=UserProfileView.as_view("settings"), methods=["POST"], endpoint="update_settings")
    user_bp.add_url_rule("/change_password", view_func=UserProfileView.change_password, methods=["POST"], endpoint="change_password")

    app.register_blueprint(user_bp)
