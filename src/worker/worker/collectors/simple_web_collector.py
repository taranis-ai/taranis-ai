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
        self.web_url: str
        self.xpath: str
        self.last_attempted = None
        self.digest_splitting_limit: int
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        super().parse_source(source)
        self.web_url = source["parameters"].get("WEB_URL", None)
        if not self.web_url:
            logger.error("No WEB_URL set")
            raise ValueError("No WEB_URL set")

    def collect(self, source, manual: bool = False):
        self.parse_source(source)
        logger.info(f"Website {source['id']} Starting collector for url: {self.web_url}")

        try:
            return self.web_collector(source, manual)
        except Exception as e:
            logger.exception(f"Simple Web Collector for {self.web_url} failed with error: {str(e)}")
            return str(e)

    def preview_collector(self, source):
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

    def web_collector(self, source, manual: bool = False):
        response = requests.head(self.web_url, headers=self.headers, proxies=self.proxies)

        if response.status_code == 429:
            logger.error("Website returned 429 Too Many Requests. Consider decreasing the REFRESH_INTERVAL")
            raise requests.exceptions.HTTPError("Website returned 429 Too Many Requests. Consider decreasing the REFRESH_INTERVAL")

        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        self.last_attempted = self.get_last_attempted(source)
        if not self.last_attempted:
            self.update_favicon(self.web_url, self.osint_source_id)

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
            "description": "",
            "id": "1",
            "last_attempted": "2000-01-01T00:00:00.000000",
            "last_collected": "2000-01-01T00:00:00.000000",
            "last_error_message": None,
            "name": "TestName",
            "parameters": {
                "ADDITIONAL_HEADERS": '{"User-Agent": "Chromium/1.0", "Authorization": "Bearer Token1234", "X-API-KEY": "12345", "Cookie": "firstcookie=1234; second-cookie=4321"}',
                "FEED_URL": "www.hello.hello.com",
                "USER_AGENT": "Mozilla/5.0",
            },
            "state": 0,
            "type": "rss_collector",
            "word_lists": [],
        }
    )


if __name__ == "__main__":
    browser_mode_test()
