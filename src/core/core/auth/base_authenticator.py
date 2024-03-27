from flask_jwt_extended import create_access_token

from core.log import logger
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User


class BaseAuthenticator:
    def get_required_credentials(self):
        return []

    def get_authenticator_name(self):
        return ""

    def __str__(self):
        return f"Authenticator: {self.get_authenticator_name()}"

    def authenticate(self, credentials):
        return BaseAuthenticator.generate_error()

    def refresh(self, user):
        return BaseAuthenticator.generate_jwt(user.username)

    @staticmethod
    def logout(token):
        if token is not None:
            TokenBlacklist.add(token)

    @staticmethod
    def initialize(app):
        pass

    @staticmethod
    def generate_error() -> tuple[dict[str, str], int]:
        return {"error": "Authentication failed"}, 401

    @staticmethod
    def generate_jwt(username: str) -> tuple[dict[str, str], int]:
        if user := User.find_by_name(username):
            logger.store_user_activity(user, "LOGIN", "Successful")
            access_token = create_access_token(
                identity=user.username,
                additional_claims={"user_claims": {"id": user.id, "name": user.name, "roles": user.get_roles()}},
            )

            return {"access_token": access_token}, 200

        logger.store_auth_error_activity(f"User doesn't exists: {username}")
        return BaseAuthenticator.generate_error()
