import requests
import logging

from worker.log import logger
from worker.types import NewsItem
from worker.collectors.base_web_collector import BaseWebCollector
from worker.collectors.playwright_manager import PlaywrightManager


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
        super().parse_source(source)
        self.web_url = source["parameters"].get("WEB_URL", None)
        if not self.web_url:
            logger.error("No WEB_URL set")
            return {"error": "No WEB_URL set"}

    def collect(self, source, manual: bool = False):
        self.parse_source(source)
        logger.info(f"Website {source['id']} Starting collector for url: {self.web_url}")

        try:
            return self.web_collector(source, manual)
        except Exception as e:
            logger.exception()
            logger.error(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")
            return str(e)

    def preview_collector(self, source):
        self.parse_source(source)
        self.news_items = self.gather_news_items()
        return self.preview(self.news_items, source)

    def handle_digests(self) -> list[NewsItem] | str:
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
            news_items = self.collect_news()
        finally:
            if self.playwright_manager:
                self.playwright_manager.stop_playwright_if_needed()

        return news_items

    def collect_news(self) -> list[NewsItem]:
        if self.digest_splitting == "true":
            return self.handle_digests()
        
        return [self.news_item_from_article(self.web_url, self.xpath)]

    def web_collector(self, source, manual: bool = False):
        response = requests.head(self.web_url, headers=self.headers, proxies=self.proxies)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(self.web_url, self.osint_source_id)
        last_modified = self.get_last_modified(response)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted and not manual:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        try:
            self.news_items = self.gather_news_items()
        except ValueError as e:
            logger.error(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")

        self.publish(self.news_items, source)
        return None


def browser_mode_test():
    collector = SimpleWebCollector()
    collector.collect(
        {
            "id": "test",
            "parameters": {
                "WEB_URL": "",
                "XPATH": "//*[@id='mCSB_1_container']",
                "DIGEST_SPLITTING": "true",
                "BROWSER_MODE": "true",
                # "PROXY_SERVER": "http://test_username:test_password@example.com:80",
                "ADDITIONAL_HEADERS:": {
                    "AUTHORIZATION": "Bearer Token1234",
                    "X-API-KEY": "12345",
                    "Cookie": "firstcookie=1234; second-cookie=4321",
                },
            },
        }
    )


if __name__ == "__main__":
    browser_mode_test()
