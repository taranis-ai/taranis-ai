import contextlib
import requests
from flask import Response, make_response, render_template, request, url_for
from flask.views import MethodView

from frontend.auth import logout
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.log import logger


class AuthView(MethodView):
    def _external_login_with_retries(self, auth_headers: dict[str, str], attempts: int = 3) -> Response:
        for attempt in range(1, attempts + 1):
            status_code = "no response"
            core_response = None

            try:
                core_response = CoreApi().external_login(auth_headers)
            except Exception as exc:
                logger.warning(f"External login request failed on attempt {attempt}: {exc}")

            if core_response is not None:
                login_response = self.login_flow(core_response)
                status_code = str(login_response.status_code)
                if login_response.status_code == 302 or attempt == attempts:
                    return login_response

            if attempt < attempts:
                logger.debug(f"External login attempt failed, retrying... Status code: {status_code}")
        return make_response(render_template("login/index.html", login_error="Login failed, no response from server"), 500)

    def login_flow(self, core_response: requests.Response) -> Response:
        if core_response is None:
            return make_response(render_template("login/index.html", login_error="Login failed, no response from server"), 500)

        if not core_response.ok:
            error_message = "Login failed"
            with contextlib.suppress(Exception):
                response_json = core_response.json()
                if isinstance(response_json, dict):
                    error_message = response_json.get("error", error_message)
            return make_response(
                render_template("login/index.html", login_error=error_message), core_response.status_code
            )

        location = request.args.get("next", url_for("base.dashboard"))
        response = Response(status=302, headers={"Location": location})

        for h in core_response.raw.headers.getlist("Set-Cookie"):
            response.headers.add("Set-Cookie", h)

        return response

    def get(self):
        if login_data := CoreApi().get_login_data():
            auth_method = login_data.get("auth_method", "database")
            auth_header_names = login_data.get("auth_headers", {})
            if auth_method == "external" and auth_header_names:
                auth_headers = {k.upper(): v for k, v in request.headers.items() if k.upper() in auth_header_names.values()}
                if auth_header_names.get("username_header") not in auth_headers:
                    logger.debug(f"Missing required auth header for external login: {auth_header_names.get('username_header')}")
                    return render_template(
                        "login/index.html",
                        notification={"message": "Missing required authentication headers - contact your admin", "error": True},
                    ), 400
                return self._external_login_with_retries(auth_headers, attempts=3)
            return render_template("login/index.html", auth_method=auth_method)

        return render_template(
            "login/index.html", notification={"message": f"API is not reachable - {Config.TARANIS_CORE_URL}", "error": True}
        ), 500

    def post(self):
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("login/index.html", login_error="Username and password are required"), 400

        try:
            core_response = CoreApi().login(username, password)
        except Exception:
            return render_template("login/index.html", login_error="Login failed, no response from server"), 500

        return self.login_flow(core_response)

    def delete(self):
        return logout()
