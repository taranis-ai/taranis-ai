from flask import request, Flask, abort
from flask.views import MethodView

from core.managers import auth_manager
from core.model.user import User


class UserInfo(MethodView):
    def get(self):
        if user := auth_manager.get_user_from_jwt():
            return user.to_detail_dict(), 200
        return abort(401)


class UserProfile(MethodView):
    def get(self):
        if user := auth_manager.get_user_from_jwt():
            return user.get_profile_json()
        return abort(401)

    def put(self):
        # sourcery skip: use-named-expression
        user = auth_manager.get_user_from_jwt()
        if not user:
            return abort(401)
        json_data = request.json
        if not json_data:
            return {"error": "No input data provided"}, 400
        return User.update_profile(user, request.json)


def initialize(app: Flask):
    base_route = "/api/users"
    app.add_url_rule(f"{base_route}/", view_func=UserInfo.as_view("user_info"))
    app.add_url_rule(f"{base_route}/profile", view_func=UserProfile.as_view("user_profile"))
    app.add_url_rule(f"{base_route}/profile/", view_func=UserProfile.as_view("user_profile_"))
