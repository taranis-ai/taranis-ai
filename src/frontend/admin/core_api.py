import requests
from flask import request
from admin.log import logger
from admin.config import Config


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

    def api_put(self, url, json_data=None) -> requests.Response:
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        return requests.put(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)

    def api_post(self, url, json_data=None) -> requests.Response:
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        return requests.post(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)

    def api_delete(self, url) -> requests.Response:
        url = f"{self.api_url}{url}"
        return requests.delete(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)

    def api_get(self, url, params: dict | None = None):
        url = f"{self.api_url}{url}"
        try:
            response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout, params=params)
        except Exception as e:
            logger.error(f"Call to {url} failed {e}")
            return None
        return self.check_response(response, url)

    def api_download(self, url, params: dict | None = None):
        url = f"{self.api_url}{url}"
        try:
            response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout, params=params, stream=True)
        except Exception as e:
            logger.error(f"Call to {url} failed {e}")
            return None
        return response

    def get_dashboard(self, query_params=None):
        return self.api_get("/dashboard", params=query_params)

    def get_users(self, query_params=None):
        return self.api_get("/config/users", params=query_params)

    def get_organizations(self, query_params=None):
        return self.api_get("/config/organizations", params=query_params)

    def export_users(self, user_ids=None):
        return self.api_download("/config/users-export", params=user_ids)

    def import_users(self, users):
        response = self.api_post("/config/users-import", json_data=users)
        return response
