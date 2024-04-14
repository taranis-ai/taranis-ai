from core.log import logger
from core.auth.base_authenticator import BaseAuthenticator


users = {"user": "user", "admin": "admin"}


class TestAuthenticator(BaseAuthenticator):
    def get_authenticator_name(self):
        return "TestAuthenticator"

    def __str__(self):
        return f"Authenticator: {self.get_authenticator_name()} Users: {users}"

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
