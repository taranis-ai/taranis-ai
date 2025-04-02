from flask import Response, jsonify
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

    def refresh(self, user):
        return BaseAuthenticator.generate_jwt(user.username)

    @staticmethod
    def logout(jti):
        TokenBlacklist.add(jti)

    @staticmethod
    def generate_error() -> Response:
        error_message = jsonify({"error": "Authentication failed"})
        error_message.status_code = 401
        return error_message

    @staticmethod
    def generate_jwt(username: str) -> Response:
        if user := User.find_by_name(username):
            logger.store_user_activity(user, "LOGIN", "Successful")
            access_token = create_access_token(
                identity=user,
                additional_claims={"user_claims": {"id": user.id, "name": user.name, "roles": user.get_roles()}},
            )
            response = jsonify({"access_token": access_token})
            response.status_code = 200
            set_access_cookies(response, access_token)
            return response

        logger.store_auth_error_activity(f"User doesn't exists: {username}")
        return BaseAuthenticator.generate_error()
