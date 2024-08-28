from flask import Response
from core.log import logger
from core.auth.base_authenticator import BaseAuthenticator
from werkzeug.security import check_password_hash
from core.model.user import User


class DatabaseAuthenticator(BaseAuthenticator):
    def __init__(self):
        self.name: str = "DatabaseAuthenticator"

    def authenticate(self, credentials: dict[str, str]) -> Response:
        username = credentials.get("username")
        password = credentials.get("password")
        if username is None or password is None:
            return BaseAuthenticator.generate_error()

        user = User.find_by_name(username)
        if user and check_password_hash(user.password, password):
            return BaseAuthenticator.generate_jwt(username)

        logger.store_auth_error_activity(f"Authentication failed with credentials: {credentials}")
        return BaseAuthenticator.generate_error()
