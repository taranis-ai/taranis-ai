import datetime
import hashlib
import uuid
import requests
import logging
import lxml.html
from trafilatura import bare_extraction

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector


class SimpleWebCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "SIMPLE_WEB_COLLECTOR"
        self.name = "Simple Web Collector"
        self.description = "Collector for gathering news with Trafilatura"

        self.news_items = []
        self.last_modified = None
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def collect(self, source):
        web_url = source["parameters"].get("WEB_URL", None)
        if not web_url:
            logger.warning("No WEB_URL set")
            return "No WEB_URL set"

        logger.info(f"Website {source['id']} Starting collector for url: {web_url}")

        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

        xpath = source["parameters"].get("XPATH", "")
        try:
            return self.web_collector(web_url, source, xpath)
        except Exception as e:
            logger.exception()
            logger.error(f"Simple Web Collector for {web_url} failed with error: {str(e)}")
            return str(e)

    def web_collector(self, web_url: str, source, xpath: str = ""):
        response = requests.head(web_url, headers=self.headers, proxies=self.proxies)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(web_url, source["id"])
        last_modified = self.get_last_modified(response)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        try:
            news_item = self.parse_web_content(web_url, source["id"], xpath)
            if news_item.get("error"):
                return news_item.get("error")
        except ValueError as e:
            logger.error(f"Simple Web Collector for {web_url} failed with error: {str(e)}")
            return str(e)

        self.publish([news_item], source)
        return None
