from flask import Response, jsonify, make_response
from flask_jwt_extended import create_access_token, set_access_cookies

from core.log import logger
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User


class BaseAuthenticator:
    def __init__(self):
        self.name: str = ""

    def __str__(self):
        return f"Authenticator: {self.name}"

    def authenticate(self, credentials):
        return BaseAuthenticator.generate_error()

    @staticmethod
    def logout(jti):
        TokenBlacklist.add(jti)

    @staticmethod
    def generate_error() -> Response:
        return make_response(jsonify({"error": "Authentication failed"}), 401)

    @staticmethod
    def complete_login(user: User) -> Response:
        user.mark_last_login()
        logger.store_user_activity(user, "LOGIN", "Successful")
        return BaseAuthenticator.issue_access_token(user)

    @staticmethod
    def issue_access_token(user: User) -> Response:
        access_token = create_access_token(
            identity=user,
            additional_claims={"user_claims": {"id": user.id, "name": user.name, "roles": user.get_roles()}},
        )
        response = make_response(jsonify({"access_token": access_token}), 200)
        set_access_cookies(response, access_token)
        return response
