from werkzeug.datastructures import Headers

from core.auth.base_authenticator import BaseAuthenticator
from core.config import Config


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
        username = credentials.get("username")
        if username is None:
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(username)

    @staticmethod
    def get_credentials(headers: Headers) -> dict[str, str]:
        return {"username": headers.get(Config.EXTERNAL_AUTH_HEADER, "")}
