from urllib.parse import quote
from flask import redirect, make_response, request
from flask_restx import Resource, reqparse, Namespace
from flask_jwt_extended import jwt_required

from core.config import Config
from core.managers import auth_manager
from core.managers.log_manager import logger


class Login(Resource):
    def get(self):
        return make_response(redirect(quote(request.args.get(key="gotoUrl", default="/"))))

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
    def get(self):
        token = request.args["jwt"] if "jwt" in request.args else None
        response = auth_manager.logout(token)

        if goto_url := request.args.get("gotoUrl"):
            url = Config.OPENID_LOGOUT_URL.replace("GOTO_URL", goto_url) if Config.OPENID_LOGOUT_URL else goto_url
            return redirect(quote(url))

        return response


def initialize(api):
    namespace = Namespace("Auth", description="Authentication related operations", path="/api/v1/auth")
    namespace.add_resource(Login, "/login")
    namespace.add_resource(Refresh, "/refresh")
    namespace.add_resource(Logout, "/logout")
    api.add_namespace(namespace)
