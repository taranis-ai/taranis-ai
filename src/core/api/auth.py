from flask_restful import Resource, reqparse, request, ResponseBase
from flask import redirect, make_response
from managers import auth_manager
from managers.auth_manager import no_auth
from config import Config


class Login(Resource):

    @no_auth
    def get(self):
        response = auth_manager.authenticate(None)

        if not isinstance(response, ResponseBase):
            if "gotoUrl" in request.args and "access_token" in response:
                redirect_response = make_response(redirect(request.args["gotoUrl"]))
                redirect_response.set_cookie('jwt', response["access_token"])
                return redirect_response

        return response

    def post(self):
        parser = reqparse.RequestParser()
        for credential in auth_manager.get_required_credentials():
            parser.add_argument(credential)
        credentials = parser.parse_args()

        return auth_manager.authenticate(credentials)


class Logout(Resource):

    @no_auth
    def get(self):
        response = auth_manager.logout()

        if not isinstance(response, ResponseBase):
            if "gotoUrl" in request.args and Config.OPENID_LOGOUT_URL:
                url = Config.OPENID_LOGOUT_URL.replace('GOTO_URL', request.args["gotoUrl"])
                return redirect(url)

        return response


def initialize(api):
    api.add_resource(Login, "/api/v1/auth/login")
    api.add_resource(Logout, "/api/v1/auth/logout")
