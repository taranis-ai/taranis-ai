import os
import re
import requests
from flask import request, Response
from flask_restful import Resource

from core.managers.auth_manager import no_auth


class Keycloak(Resource):
    matchers = [
        re.compile(
            r"^"
            + re.escape(str(os.environ["TARANIS_NG_KEYCLOAK_URL"]))
            + r"\/auth\/realms\/taranis_ng\/protocol\/openid-connect\/auth\?(response_type\=code)\&(client_id\=taranis_ng)\&(redirect_uri\=(https?%3[aA]\/\/[a-z0-9A-Z%\/\.\-_]*|https?%3[aA]%2[fF]%2[fF][a-z0-9A-Z%\/\.\-_]*))$"  # noqa
        ),  # noqa
        # login url
        re.compile(
            r"^"
            + re.escape(str(os.environ["TARANIS_NG_KEYCLOAK_URL"]))
            + r"\/auth\/realms\/taranis_ng\/login-actions\/authenticate(\??session_code\=[a-zA-Z0-9\-_]+)?(\&?\??execution\=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12})?(\&?\??client_id\=taranis_ng)?(\&?\??tab_id=[a-zA-Z0-9\-_]+)?$"  # noqa
        ),  # noqa
        # login submit url
        re.compile(
            r"^"
            + re.escape(str(os.environ["TARANIS_NG_KEYCLOAK_URL"]))
            + r"\/auth\/realms\/taranis_ng\/protocol\/openid-connect\/logout\?(redirect_uri\=(https?%3[aA]\/\/[a-z0-9A-Z%\/\.\-_]*|https?%3[aA]%2[fF]%2[fF][a-z0-9A-Z%\/\.\-_]*))$"  # noqa
        ),
        # logout url
        re.compile(
            r"^"
            + re.escape(str(os.environ["TARANIS_NG_KEYCLOAK_URL"]))
            + r"\/auth\/resources\/([^\.]*|[^\.]*\.[^\.]*|[^\.]*\.[^\.]*\.[^\.]*)$"
        ),
        # resources url
        re.compile(
            r"^"
            + re.escape(str(os.environ["TARANIS_NG_KEYCLOAK_URL"]))
            + r"\/auth\/realms\/taranis_ng\/login-actions\/required-action(\??session_code\=[a-zA-Z0-9\-_]+)?(\??\&?execution\=(UPDATE_PASSWORD))(\&?\??client_id\=taranis_ng)?(\&?\??tab_id=[a-zA-Z0-9\-_]+)?$"  # noqa
        ),
        # reset password url
    ]

    @no_auth
    def proxy(self):
        allowed = any(m.match(request.url) for m in self.matchers)
        if not allowed:
            return {"error": "Access forbidden"}, 403

        try:
            resp = requests.request(
                method=request.method,
                url=request.url.replace(
                    str(os.environ["TARANIS_NG_KEYCLOAK_URL"]) + "/",
                    os.getenv("TARANIS_NG_KEYCLOAK_INTERNAL_URL"),
                    1,
                ),
                headers={key: value for (key, value) in request.headers if key != "Host"},
                data=request.get_data(),
                cookies=request.cookies,
                proxies={"http": None, "https": None},
                allow_redirects=False,
            )

            excluded_headers = [
                "content-encoding",
                "content-length",
                "transfer-encoding",
                "connection",
            ]
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

            return Response(resp.content, resp.status_code, headers)
        except Exception:
            return {"error": "Internal server error"}, 500

    def get(self, path):
        return self.proxy()

    def post(self, path):
        return self.proxy()

    def put(self, path):
        return self.proxy()

    def delete(self, path):
        return self.proxy()


def initialize(api):
    api.add_resource(Keycloak, "/api/v1/auth/keycloak/<path:path>")
