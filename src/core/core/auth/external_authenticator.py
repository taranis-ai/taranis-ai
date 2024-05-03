from core.auth.base_authenticator import BaseAuthenticator


class ExternalAuthenticator(BaseAuthenticator):
    """
    ExternalAuthenticator assuems that the user is already authenticated by an external service.
    For example Basic Authentiction or TLS Client Certificate Authentication.
    It only requires the username to generate a JWT token.
    """

    def get_authenticator_name(self):
        return "ExternalAuthenticator"

    def __str__(self):
        return f"Authenticator: {self.get_authenticator_name()}"

    def authenticate(self, credentials: dict[str, str]) -> tuple[dict[str, str], int]:
        username = credentials.get("username")
        if username is None:
            return BaseAuthenticator.generate_error()
        return BaseAuthenticator.generate_jwt(username)
