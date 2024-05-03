import requests
import logging

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector
from worker.types import NewsItem


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
        self.digest_splitting_limit = None
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        self.web_url = source["parameters"].get("WEB_URL", None)
        if not self.web_url:
            logger.warning("No WEB_URL set")
            return {"error": "No WEB_URL set"}

        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))
        self.xpath = source["parameters"].get("XPATH", "")
        super().parse_source(source)

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
        news_items = self.gather_news_items(source)
        return self.preview(news_items, source)

    def handle_digests(self) -> list[dict] | str:
        web_content = self.parse_web_content(self.web_url, self.xpath)
        self.split_digest_urls = self.get_urls(web_content["content"])
        logger.info(f"RSS-Feed {self.source_id} returned {len(self.split_digest_urls)} available URLs")

        return self.parse_digests()

    def gather_news_items(self, source) -> list[NewsItem]:
        digest_splitting = source["parameters"].get("DIGEST_SPLITTING", False)
        if digest_splitting == "true":
            return self.handle_digests()
        return [self.news_item_from_article(self.web_url, self.xpath)]

    def web_collector(self, source):
        response = requests.head(self.web_url, headers=self.headers, proxies=self.proxies)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(self.web_url, self.source_id)
        last_modified = self.get_last_modified(response)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        try:
            news_items = self.gather_news_items(source)
        except ValueError as e:
            logger.error(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")

        self.publish(news_items, source)
        return None
