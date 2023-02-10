from werkzeug.urls import url_quote
from flask import redirect, make_response
from flask_restful import Resource, reqparse, request, ResponseBase
from flask_jwt_extended import jwt_required

from core.config import Config
from core.managers import auth_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import no_auth


class Login(Resource):
    @no_auth
    def get(self):
        response = auth_manager.authenticate(None)
        if not isinstance(response, ResponseBase) and "access_token" in response:
            goto_url = request.args.get(key="gotoUrl", default="/")
            redirect_response = make_response(redirect(goto_url))
            redirect_response.set_cookie("jwt", response["access_token"])
            return redirect_response
        return response

    def post(self):
        parser = reqparse.RequestParser()
        logger.log_debug(auth_manager.get_required_credentials())
        for credential in auth_manager.get_required_credentials():
            parser.add_argument(credential, location=["form", "values", "json"])
        credentials = parser.parse_args()
        return auth_manager.authenticate(credentials)


class Refresh(Resource):
    @jwt_required()
    def get(self):
        return auth_manager.refresh(auth_manager.get_user_from_jwt())


class Logout(Resource):
    @no_auth
    def get(self):
        token = request.args["jwt"] if "jwt" in request.args else None
        response = auth_manager.logout(token)

        if not isinstance(response, ResponseBase) and "gotoUrl" in request.args:
            goto_url = request.args["gotoUrl"]
            url = Config.OPENID_LOGOUT_URL.replace("GOTO_URL", url_quote(goto_url)) if Config.OPENID_LOGOUT_URL else goto_url
            return redirect(url)

        return response


def initialize(api):
    api.add_resource(Login, "/api/v1/auth/login")
    api.add_resource(Refresh, "/api/v1/auth/refresh")
    api.add_resource(Logout, "/api/v1/auth/logout")
