from core.managers.log_manager import logger
from core.auth.base_authenticator import BaseAuthenticator
from werkzeug.security import check_password_hash
from core.model.user import User


class DatabaseAuthenticator(BaseAuthenticator):
    def get_authenticator_name(self):
        return "DatabaseAuthenticator"

    def get_database_uri(self):
        return "DatabaseAuthenticator"

    def __str__(self):
        return f"Authenticator: {self.get_authenticator_name()} DB: {self.get_database_uri()}"

    def get_required_credentials(self):
        return ["username", "password"]

    def authenticate(self, credentials):
        if credentials is None:
            return BaseAuthenticator.generate_error()
        if "username" not in credentials or "password" not in credentials:
            return BaseAuthenticator.generate_error()

        user = User.find(credentials["username"])

        if user and check_password_hash(user.password, credentials["password"]):
            return BaseAuthenticator.generate_jwt(credentials["username"])

        logger.store_auth_error_activity(f"Authentication failed with credentials: {str(credentials)}")
        return BaseAuthenticator.generate_error()
