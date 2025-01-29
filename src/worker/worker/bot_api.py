import requests
from urllib.parse import urlencode

from worker.log import logger
from worker.config import Config


class BotApi:
    def __init__(self, bot_endpoint: str):
        self.api_url = bot_endpoint
        self.api_key = Config.BOT_API_KEY
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION
        self.timeout = Config.REQUESTS_TIMEOUT

    def get_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

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
