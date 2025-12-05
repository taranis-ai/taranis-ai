import datetime
import logging

import requests

from worker.collectors.base_web_collector import BaseWebCollector
from worker.collectors.playwright_manager import PlaywrightManager
from worker.log import logger
from worker.types import NewsItem


class SimpleWebCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type: str = "SIMPLE_WEB_COLLECTOR"
        self.name: str = "Simple Web Collector"
        self.description: str = "Collector for gathering news with Trafilatura"

        self.news_items: list[NewsItem] = []
        self.web_url: str
        self.xpath: str
        self.last_attempted: datetime.datetime | None = None
        self.digest_splitting_limit: int
        logger_trafilatura: logging.Logger = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source: dict):
        super().parse_source(source)
        self.web_url = source["parameters"].get("WEB_URL", None)
        if not self.web_url:
            raise ValueError("No WEB_URL set")

    def collect(self, source: dict, manual: bool = False):
        self.parse_source(source)
        return self.web_collector(source, manual)

    def preview_collector(self, source: dict) -> list[dict]:
        self.parse_source(source)
        self.news_items = self.gather_news_items()
        return self.preview(self.news_items, source)

    def handle_digests(self) -> list[NewsItem]:
        if not self.xpath:
            raise ValueError("No XPATH set for digest splitting")

        web_content, _ = self.fetch_article_content(self.web_url, self.xpath)

        if content := self.xpath_extraction(web_content, self.xpath, False):
            self.split_digest_urls = self.get_urls(self.web_url, content)
            logger.info(f"Digest splitting {self.osint_source_id} returned {len(self.split_digest_urls)} available URLs")

            return self.parse_digests()

        return []

    def gather_news_items(self) -> list[NewsItem]:
        if self.browser_mode == "true":
            self.playwright_manager = PlaywrightManager(self.proxies, self.headers)
        try:
            self.news_items = self.collect_news()
        finally:
            if self.playwright_manager:
                self.playwright_manager.stop_playwright_if_needed()

        return self.news_items

    def collect_news(self) -> list[NewsItem]:
        if self.digest_splitting == "true":
            return self.handle_digests()

        return [self.news_item_from_article(self.web_url, self.xpath)]

    def web_collector(self, source: dict, manual: bool = False):
        response = requests.head(self.web_url, headers=self.headers, proxies=self.proxies)

        if response.status_code == 429:
            raise requests.exceptions.HTTPError(f"{self.web_url} returned 429 Too Many Requests. Consider decreasing the REFRESH_INTERVAL")
        response.raise_for_status()

        self.last_attempted = self.get_last_attempted(source)
        if not self.last_attempted:
            self.update_favicon(self.web_url, self.osint_source_id)
        self.news_items = self.gather_news_items()
        return self.publish(self.news_items, source)

    def manual_collect(self, source_parameters: dict | None = None):
        source_parameters = source_parameters or {}
        source_parameters["id"] = "manual"
        self.parse_source(source_parameters)
        self.news_items = self.gather_news_items()
        return self.publish(self.news_items, source_parameters)
