import urllib
import requests
import hashlib
from collectors.managers.log_manager import logger
from collectors.config import Config


class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_NG_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = self.get_headers()
        self.collector_id = self.get_collector_id()

    def get_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def get_collector_id(self):
        uid = self.api_url + self.api_key
        return int(hashlib.sha1(uid.encode("utf-8")).hexdigest(), 16) % (10**16)

    def get_osint_sources(self, collector_type):
        try:
            response = requests.get(
                self.api_url
                + "/api/v1/collectors/"
                + self.collector_id
                + "/osint-sources?collector_type="
                + urllib.parse.quote(collector_type),
                headers=self.headers,
            )
            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot get OSINT Sources")
            return None, 400

    def register_collector_node(self):
        try:
            collector_info = {"id": self.collector_id}
            response = requests.post(
                f"{self.api_url}/api/v1/collectors/node/{self.collector_id}",
                json=collector_info,
                headers=self.headers,
            )

            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot register Collector node")
            return None, 400

    def update_collector_status(self):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/collectors/{self.collector_id}",
                headers=self.headers,
            )

            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot update Collector status")
            return None, 400

    def add_news_items(self, news_items):
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/collectors/news-items",
                json=news_items,
                headers=self.headers,
            )

            return response.status_code
        except Exception:
            logger.log_debug_trace("Cannot add Newsitem")
            return None, 400
