from werkzeug.datastructures import Headers
from flask_jwt_extended import create_access_token

from core.auth.base_authenticator import BaseAuthenticator
from core.config import Config
from core.model.user import User
from core.log import logger


class ExternalAuthenticator(BaseAuthenticator):
    """
    ExternalAuthenticator assuems that the user is already authenticated by an external service.
    For example Basic Authentiction or TLS Client Certificate Authentication.
    The field 'username' is compared against the Header configured via EXTERNAL_AUTH_HEADER.
    ü
    """

    def __init__(self):
        self.name: str = "ExternalAuthenticator"

    def authenticate(self, credentials: dict[str, str]) -> tuple[dict[str, str], int]:
        logger.debug(f"{credentials=}")
        username = credentials.get("username")
        if not username:
            return BaseAuthenticator.generate_error()

        user = self.create_user_if_not_exists(username, credentials)
        logger.store_user_activity(user, "LOGIN", "Successful")

        access_token = create_access_token(
            identity=user,
            additional_claims={"user_claims": {"id": user.id, "name": user.name, "roles": user.get_roles()}},
        )

        return {"access_token": access_token}, 200

    @staticmethod
    def get_credentials(headers: Headers) -> dict[str, str]:
        return {
            "username": headers.get(Config.EXTERNAL_AUTH_USER, ""),
            "roles": headers.get(Config.EXTERNAL_AUTH_ROLES, ""),
            "name": headers.get(Config.EXTERNAL_AUTH_NAME, ""),
            "organization": headers.get(Config.EXTERNAL_AUTH_ORGANIZATION, ""),
        }

    def create_user_if_not_exists(self, username: str, credentials: dict[str, str]) -> "User":
        name = credentials.get("name")
        organization = credentials.get("organization")
        roles = credentials.get("roles")

        if user := User.find_by_name(username):
            return user

        return User.add({"username": username, "name": name, "organization": organization, "roles": roles})
