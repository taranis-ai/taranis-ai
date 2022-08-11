import urllib
import requests
from collectors.managers.log_manager import logger
from collectors.config import Config


class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_NG_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.config_file = Config.COLLECTOR_CONFIG_FILE
        self.collector_id = self.get_collector_id()

    def get_collector_id(self):
        try:
            with open(self.config_file, "r") as file:
                return file.read().strip()
        except Exception:
            logger.log_debug_trace("Cannot read collector config file")
            return "Cannot read collector config file.", 0

    def get_osint_sources(self, collector_type):
        try:
            response = requests.get(
                self.api_url
                + "/api/v1/collectors/"
                + urllib.parse.quote(self.collector_id)
                + "/osint-sources?api_key="
                + urllib.parse.quote(self.api_key)
                + "&collector_type="
                + urllib.parse.quote(collector_type),
                headers=self.headers,
            )
            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot get OSINT Sources")
            return None, 400

    def update_collector_status(self):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/collectors/{urllib.parse.quote(self.collector_id)}",
                headers=self.headers,
            )

            return response.json(), response.status_code
        except Exception as ex:
            logger.log_debug_trace("Cannot update Collector status")
            return ex, 400

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
