from core.log import logger
from core.auth.base_authenticator import BaseAuthenticator


users = {"user": "user", "admin": "admin"}


class TestAuthenticator(BaseAuthenticator):
    def __init__(self):
        self.name = "TestAuthenticator"

    def authenticate(self, credentials: dict[str, str]) -> tuple[dict[str, str], int]:
        logger.log_debug(f"TEST AUTH with {credentials}")
        if credentials is None:
            return BaseAuthenticator.generate_error()
        if "username" not in credentials or "password" not in credentials:
            return BaseAuthenticator.generate_error()
        if users[credentials["username"]] == credentials["password"]:
            return BaseAuthenticator.generate_jwt(credentials["username"])

        logger.store_auth_error_activity(f"Authentication failed with credentials: {credentials}")
        return BaseAuthenticator.generate_error()
