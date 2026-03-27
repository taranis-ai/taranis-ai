from urllib.parse import urlencode

import requests

from worker.config import Config
from worker.log import logger


class BotApi:
    def __init__(
        self,
        bot_endpoint: str,
        bot_api_key: str | None = Config.BOT_API_KEY,
        requests_timeout: int | str | None = None,
    ):
        self.api_url = bot_endpoint
        self.api_key = bot_api_key
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION
        self.timeout = self._resolve_timeout(requests_timeout)

    def get_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def update_parameters(self, api_url: str, api_key: str | None = None):
        self.api_url = api_url
        self.api_key = api_key or Config.BOT_API_KEY

    @staticmethod
    def _resolve_timeout(timeout_value: int | str | None) -> int:
        if timeout_value in [None, ""]:
            return Config.REQUESTS_TIMEOUT
        try:
            timeout = int(timeout_value)
        except (TypeError, ValueError):
            return Config.REQUESTS_TIMEOUT
        return timeout if timeout > 0 else Config.REQUESTS_TIMEOUT

    def check_response(self, response: requests.Response, url: str):
        try:
            if response.ok:
                return response.json()
        except Exception:
            logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        return None

    def api_post(self, url, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.post(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)
        return self.check_response(response, url)

    def api_get(self, url: str, params=None):
        url = f"{self.api_url}{url}"
        if params:
            url += f"?{urlencode(params)}"
        response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        return self.check_response(response, url)
