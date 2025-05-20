from flask import Flask, render_template, Blueprint
from flask.views import MethodView
from flask_jwt_extended import current_user

from frontend.auth import auth_required


class UserProfile(MethodView):
    @auth_required()
    def get(self):
        return render_template("user_profile/profile.html", user=current_user)


class UserSettings(MethodView):
    @auth_required()
    def get(self):
        return render_template("user_profile/settings.html", user=current_user)


def init(app: Flask):
    user_bp = Blueprint("user", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    user_bp.add_url_rule("/profile", view_func=UserProfile.as_view("user_profile"))
    user_bp.add_url_rule("/settings", view_func=UserSettings.as_view("user_settings"))

    app.register_blueprint(user_bp)
