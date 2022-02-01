from auth.base_authenticator import BaseAuthenticator
from authlib.integrations.flask_client import OAuth

oauth = OAuth()

class OpenIDAuthenticator(BaseAuthenticator):

    @staticmethod
    def initialize(app):
        oauth.init_app(app)
        oauth.register(
            name='openid',
            client_id=app.config.get('OPENID_CLIENT_ID'),
            client_secret=app.config.get('OPENID_CLIENT_SECRET'),
            server_metadata_url= app.config.get('OPENID_METADAT_URL'),
        )

    def authenticate(self, credentials):
        token = oauth.openid.authorize_access_token()
        user = oauth.openid.userinfo()
        if user.preferred_username:
            print(user.preferred_username)
            return BaseAuthenticator.generate_jwt(user)

        return BaseAuthenticator.generate_error()

    @staticmethod
    def logout(token):
        BaseAuthenticator.logout(token)
