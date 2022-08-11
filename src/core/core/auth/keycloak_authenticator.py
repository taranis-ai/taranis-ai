from os import environ
from flask_jwt_extended import get_jwt
from flask_restful import request
from requests import post
from requests.auth import HTTPBasicAuth

from core.managers.log_manager import logger
from core.auth.base_authenticator import BaseAuthenticator


class KeycloakAuthenticator(BaseAuthenticator):
    def authenticate(self, credentials):

        # check if code and session_state are present in keycloak callback
        if "code" not in request.args or "session_state" not in request.args:
            return {"error": "Missing code or session_state parameters"}, 400

        # verify code and get JWT token from keycloak
        response = post(
            url=environ.get("TARANIS_NG_KEYCLOAK_INTERNAL_URL") + "auth/realms/taranis_ng/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "code": request.args["code"],  # code from url
                "redirect_uri": "/".join(request.headers.get("Referer").split("/")[0:3]) + "/login"
                # original redirect_uri (host needs to match)
            },
            auth=HTTPBasicAuth(
                environ.get("TARANIS_NG_KEYCLOAK_CLIENT_ID"),
                environ.get("TARANIS_NG_KEYCLOAK_CLIENT_SECRET"),
            ),
            # do not forget credentials
            proxies={"http": None, "https": None},
            allow_redirects=False,
        )

        data = None

        try:
            # get json data from response
            data = response.json()
        except Exception:
            logger.store_auth_error_activity("Keycloak returned an unexpected response.")
            return {"error": "Internal server error"}, 500

        try:
            # decode token to get user data
            data = get_jwt()["access_token"]
            user = auth_manager.get_user_from_jwt()
        except Exception:
            logger.store_auth_error_activity("Keycloak returned invalid access_token.")
            return {"error": "Internal server error"}, 500

        # generate custom token
        return BaseAuthenticator.generate_jwt(data["preferred_username"])
