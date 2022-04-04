from managers import log_manager
from auth.base_authenticator import BaseAuthenticator


users = {"user": "user", "user2": "user", "admin": "admin", "customer": "customer"}


class TestAuthenticator(BaseAuthenticator):

    def get_required_credentials(self):
        return ["username", "password"]

    def authenticate(self, credentials):
        log_manager.log_debug(f"TEST AUTH with {credentials}")
        if credentials is None:
            return BaseAuthenticator.generate_error()
        if "username" not in credentials or "password" not in credentials:
            return BaseAuthenticator.generate_error()
        if credentials["username"] in users:
            if users[credentials["username"]] == credentials["password"]:
                return BaseAuthenticator.generate_jwt(credentials["username"])

        log_manager.store_auth_error_activity("Authentication failed with credentials: " + str(credentials))

        return BaseAuthenticator.generate_error()
