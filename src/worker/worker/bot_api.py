from urllib.parse import urlencode

import niquests as requests

from worker.config import Config
from worker.log import logger


class BotServiceUnavailableError(RuntimeError):
    public_message = "Bot service is unavailable. Check its configured endpoint and ensure the service is running."
    reason = "bot_service_unavailable"
    retryable = True

    def __init__(self):
        super().__init__(self.public_message)


class BotApi:
    def __init__(
        self,
        bot_endpoint: str,
        bot_api_key: str | None = Config.BOT_API_KEY,
        requests_timeout: int | None = None,
    ):
        self.api_url = bot_endpoint
        self.api_key = bot_api_key
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION
        self.timeout = requests_timeout or Config.REQUESTS_TIMEOUT

    def get_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def update_parameters(self, api_url: str, api_key: str | None = None):
        self.api_url = api_url
        self.api_key = api_key or Config.BOT_API_KEY

    def check_response(self, response: requests.Response, url: str):
        try:
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.JSONDecodeError, requests.exceptions.HTTPError) as exc:
            logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
            raise BotServiceUnavailableError from exc
        return None

    def api_post(self, url: str, json_data: dict | None = None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        try:
            response = requests.post(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error(f"Bot service POST request to {url} failed: {exc}")
            raise BotServiceUnavailableError from None
        return self.check_response(response, url)

    def api_get(self, url: str, params: dict | None = None):
        url = f"{self.api_url}{url}"
        if params:
            url += f"?{urlencode(params)}"
        try:
            response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error(f"Bot service GET request to {url} failed: {exc}")
            raise BotServiceUnavailableError from None
        return self.check_response(response, url)
