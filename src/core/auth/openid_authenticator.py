from flask_oidc import OpenIDConnect

from auth.base_authenticator import BaseAuthenticator

oidc = OpenIDConnect()


class OpenIDAuthenticator(BaseAuthenticator):

    @staticmethod
    def initialize(app):
        oidc.init_app(app)

    @oidc.require_login
    def authenticate(self, credentials):
        access_token = oidc.get_access_token()
        valid = oidc.validate_token(access_token)

        if valid is True:
            return BaseAuthenticator.generate_jwt(oidc.user_getfield('preferred_username'))

        return BaseAuthenticator.generate_error()

    @staticmethod
    def logout(token):
        BaseAuthenticator.logout(token)
        oidc.logout()
