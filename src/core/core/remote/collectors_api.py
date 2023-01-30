import requests
from core.managers.log_manager import logger


class CollectorsApi:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url[:-1] if api_url.endswith("/") else api_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_collectors_info(self):
        collector_endpoint = f"{self.api_url}/api/v1/collectors"
        logger.log_debug(f"Getting Collector Infos from: {collector_endpoint}")
        try:
            response = requests.get(collector_endpoint, headers=self.headers)
        except Exception as e:
            return str(e), 500

        return response.json(), response.status_code

    def refresh_collector(self, collector_type):
        response = requests.put(f"{self.api_url}/api/v1/collectors/{collector_type}", headers=self.headers)

        return response.status_code

    def refresh_collectors(self):
        response = requests.post(f"{self.api_url}/api/v1/collectors", headers=self.headers)

        return response.status_code
