from flask import Response
from core.log import logger
from core.auth.base_authenticator import BaseAuthenticator


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
        logger.debug(f"DEV AUTH with {credentials}")

        username, password = credentials.get("username"), credentials.get("password")

        if not username or not password:
            return BaseAuthenticator.generate_error()

        if users.get(username) == password:
            return BaseAuthenticator.generate_jwt(username)

        logger.store_auth_error_activity(f"Authentication failed with credentials: {credentials}")
        return BaseAuthenticator.generate_error()
