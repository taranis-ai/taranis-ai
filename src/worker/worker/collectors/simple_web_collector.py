import requests
import logging

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector


class SimpleWebCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "SIMPLE_WEB_COLLECTOR"
        self.name = "Simple Web Collector"
        self.description = "Collector for gathering news with Trafilatura"

        self.news_items = []
        self.web_url = None
        self.xpath = None
        self.last_modified = None
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        self.web_url = source["parameters"].get("WEB_URL", None)
        if not self.web_url:
            logger.warning("No WEB_URL set")
            return {"error": "No WEB_URL set"}

        self.set_proxies(source["parameters"].get("PROXY_SERVER", None))

        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

        self.xpath = source["parameters"].get("XPATH", "")

    def collect(self, source):
        self.parse_source(source)
        logger.info(f"Website {source['id']} Starting collector for url: {self.web_url}")

        try:
            return self.web_collector(source)
        except Exception as e:
            logger.exception()
            logger.error(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")
            return str(e)

    def preview_collector(self, source):
        self.parse_source(source)
        news_item = self.parse_web_content(self.web_url, source["id"])

        return self.preview([news_item], source)

    def web_collector(self, source):
        response = requests.head(self.web_url, headers=self.headers, proxies=self.proxies)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(self.web_url, source["id"])
        last_modified = self.get_last_modified(response)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        try:
            news_item = self.parse_web_content(self.web_url, source["id"], self.xpath)
            if news_item.get("error"):
                return news_item.get("error")
        except ValueError as e:
            logger.error(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")

        self.publish([news_item], source)
        return None
