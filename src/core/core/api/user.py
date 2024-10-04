from flask_jwt_extended import jwt_required, current_user
from flask import Blueprint, request, Flask
from flask.views import MethodView

from core.model.user import User
from core.managers.sse_manager import sse_manager
from core.config import Config


class UserInfo(MethodView):
    @jwt_required()
    def get(self):
        return current_user.to_detail_dict(), 200


class UserProfile(MethodView):
    @jwt_required()
    def get(self):
        return current_user.get_profile(), 200

    @jwt_required()
    def put(self):
        if not (json_data := request.json):
            return {"error": "No input data provided"}, 400
        return User.update_profile(current_user, json_data)


class SSEConnected(MethodView):
    @jwt_required()
    def post(self):
        sse_manager.connected()
        return {"connected": True}, 200


def initialize(app: Flask):
    user_bp = Blueprint("user", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/users")

    user_bp.add_url_rule("/", view_func=UserInfo.as_view("user_info"))
    user_bp.add_url_rule("/profile", view_func=UserProfile.as_view("user_profile"))
    user_bp.add_url_rule("/sse-connected", view_func=SSEConnected.as_view("sse_connected"))

    app.register_blueprint(user_bp)
