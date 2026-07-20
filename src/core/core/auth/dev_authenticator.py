from flask import Response

from core.auth.base_authenticator import BaseAuthenticator
from core.log import logger
from core.model.user import User


users = {"user": "user", "admin": "admin"}


class DevAuthenticator(BaseAuthenticator):
    """
    DevAuthenticator is a non-production authenticator for development and testing purposes.

    This authenticator is intended for development and testing environments
    only. It provides a simple authentication mechanism using a predefined
    set of users and passwords. Do not use this authenticator in production
    environments.
    """

    def __init__(self):
        self.name = "DevAuthenticator"

    def authenticate(self, credentials: dict[str, str]) -> Response:
        username, password = credentials.get("username"), credentials.get("password")
        logger.debug("DEV AUTH attempt for username: %s", username)

        if not username or not password:
            return BaseAuthenticator.generate_error()

        if users.get(username) == password and (user := User.find_by_name(username)):
            return BaseAuthenticator.complete_login(user)

        logger.store_auth_error_activity(f"Authentication failed for username: {username}")
        return BaseAuthenticator.generate_error()
