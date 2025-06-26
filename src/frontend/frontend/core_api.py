import requests
from flask import request, Response
from frontend.log import logger
from frontend.config import Config
from werkzeug.wsgi import wrap_file
from typing import cast, IO


class CoreApi:
    def __init__(self, jwt_token=None):
        self.api_url = Config.TARANIS_CORE_URL
        self.jwt_token = self.get_jwt_from_request()
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION
        self.timeout = Config.REQUESTS_TIMEOUT

    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.jwt_token}", "Content-type": "application/json"}

    def get_jwt_from_request(self):
        return request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME)

    def check_response(self, response: requests.Response, url: str):
        try:
            if response.ok:
                return response.json()
        except Exception:
            logger.error(f"(catched) Call to {url} failed {response.status_code}: {response.text}")
        logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        return None

    def check_if_api_connected(self):
        try:
            url = f"{self.api_url}/isalive"
            response = requests.get(url=url, verify=self.verify, timeout=self.timeout)
            if response.ok and response.json().get("isalive") is True:
                return True

            logger.error(f"API connection failed: {response.status_code} - {response.text}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection failed: {e}")
        return False

    def api_put(self, endpoint: str, json_data=None) -> requests.Response:
        if not json_data:
            json_data = {}
        logger.debug(f"PUT {endpoint} with data: {json_data}")
        return requests.put(url=f"{self.api_url}{endpoint}", headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)

    def api_post(self, endpoint: str, json_data=None) -> requests.Response:
        if not json_data:
            json_data = {}
        return requests.post(url=f"{self.api_url}{endpoint}", headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)

    def api_delete(self, endpoint: str) -> requests.Response:
        return requests.delete(url=f"{self.api_url}{endpoint}", headers=self.headers, verify=self.verify, timeout=self.timeout)

    def api_get(self, endpoint: str, params: dict | None = None):
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout, params=params)
        except Exception as e:
            logger.error(f"Call to {url} failed {e}")
            return None
        return self.check_response(response, url)

    def api_download(self, endpoint: str, params: dict | None = None) -> requests.Response:
        url = f"{self.api_url}{endpoint}"
        return requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout, params=params, stream=True)

    def get_users(self, query_params=None):
        return self.api_get("/config/users", params=query_params)

    def get_organizations(self, query_params=None):
        return self.api_get("/config/organizations", params=query_params)

    def export_users(self, user_ids=None):
        try:
            return self.api_download("/config/users-export", params=user_ids)
        except Exception as e:
            logger.error(f"Export users failed: {e}")
            return None

    def import_users(self, users):
        return self.api_post("/config/users-import", json_data=users)

    def import_word_lists(self, word_lists):
        return self.api_post("/config/import-word-lists", json_data=word_lists)

    def export_word_lists(self, word_list_ids=None):
        try:
            return self.api_download("/config/export-word-lists", params=word_list_ids)
        except Exception as e:
            logger.error(f"Export word lists failed: {e}")
            return None

    def import_sources(self, sources):
        return self.api_post("/config/import-osint-sources", json_data=sources)

    def export_sources(self, source_ids=None):
        try:
            return self.api_download("/config/export-osint-sources", params=source_ids)
        except Exception as e:
            logger.error(f"Export sources failed: {e}")
            return None

    def load_default_osint_sources(self):
        try:
            return self.api_get("/static/default_sources.json")
        except Exception as e:
            logger.error(f"Load default OSINT sources failed: {e}")
            return None

    def collect_osint_source_preview(self, osint_source_id):
        try:
            return self.api_post(f"/config/osint-sources/{osint_source_id}/preview")
        except Exception as e:
            logger.error(f"Collect OSINT source preview failed: {e}")
            return None

    def collect_osint_source(self, osint_source_id):
        try:
            return self.api_post(f"/config/osint-sources/{osint_source_id}/collect")
        except Exception as e:
            logger.error(f"Collect OSINT source failed: {e}")
            return None

    def collect_all_osint_sources(self):
        try:
            return self.api_post("/config/osint-sources/collect")
        except Exception as e:
            logger.error(f"Collect OSINT sources failed: {e}")
            return None

    def load_default_word_lists(self):
        try:
            return self.api_get("/static/default_word_lists.json")
        except Exception as e:
            logger.error(f"Load default word lists failed: {e}")
            return None

    def import_report_item_types(self, report_item_types):
        return self.api_post("/config/import-report-item-types", json_data=report_item_types)

    def export_report_item_types(self, report_item_type_ids=None):
        try:
            return self.api_download("/config/export-report-item-types", params=report_item_type_ids)
        except Exception as e:
            logger.error(f"Export report item types failed: {e}")
            return None

    def login(self, username, password):
        data = {"username": username, "password": password}
        return self.api_post("/auth/login", json_data=data)

    def logout(self):
        return self.api_delete("/auth/logout")

    @staticmethod
    def stream_proxy(response: requests.Response, fallback_filename: str) -> Response:
        disposition = response.headers.get("Content-Disposition", f"attachment; filename={fallback_filename}")

        file_wrapper = wrap_file(
            request.environ,
            cast(IO[bytes], response.raw),
        )

        return Response(
            file_wrapper,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/json"),
            headers={"Content-Disposition": disposition},
            direct_passthrough=True,
        )
