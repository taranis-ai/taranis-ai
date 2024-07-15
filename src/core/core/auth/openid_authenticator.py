from authlib.integrations.flask_client import OAuth

from core.auth.base_authenticator import BaseAuthenticator


class OpenIDAuthenticator(BaseAuthenticator):
    def __init__(self, app):
        self.name = "OpenIDAuthenticator"
        self.oauth = OAuth()
        self.oauth.init_app(app)
        self.oauth.register(
            name="openid",
            client_id=app.config.get("OPENID_CLIENT_ID"),
            client_secret=app.config.get("OPENID_CLIENT_SECRET"),
            server_metadata_url=app.config.get("OPENID_METADATA_URL"),
        )

    def authenticate(self, credentials):
        # self.oauth.openid.authorize_access_token()
        # user = oauth.openid.userinfo()
        # if user.preferred_username:
        #     print(user.preferred_username)
        #     return BaseAuthenticator.generate_jwt(user)

        raise NotImplementedError("Authenticator Not implemented")
