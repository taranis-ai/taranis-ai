from flask import request, Flask
from flask.views import MethodView

from core.model.user import User
from flask_jwt_extended import jwt_required, current_user


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


def initialize(app: Flask):
    base_route = "/api/users"
    app.add_url_rule(f"{base_route}/", view_func=UserInfo.as_view("user_info"))
    app.add_url_rule(f"{base_route}/profile", view_func=UserProfile.as_view("user_profile"))
    app.add_url_rule(f"{base_route}/profile/", view_func=UserProfile.as_view("user_profile_"))
