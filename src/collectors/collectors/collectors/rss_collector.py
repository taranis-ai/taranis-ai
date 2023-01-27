import datetime
import hashlib
import uuid
import traceback
import re
import feedparser
import requests
from bs4 import BeautifulSoup
import dateutil.parser as dateparser

from .base_collector import BaseCollector
from collectors.managers.log_manager import logger
from shared.schema.news_item import NewsItemData


class RSSCollector(BaseCollector):
    type = "RSS_COLLECTOR"
    name = "RSS Collector"
    description = "Collector for gathering data from RSS feeds"

    news_items = []
    proxies = None
    headers = {}

    def set_proxies(self, proxy_server: str):
        self.proxies = {"http": proxy_server, "https": proxy_server, "ftp": proxy_server}

    def make_request(self, url: str) -> None | requests.Response:
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            if not response.ok:
                return None
        except Exception:
            return None

        return response

    def get_article_content(self, link_for_article: str) -> str:
        try:
            html_content = self.make_request(link_for_article)
            if html_content is None:
                return ""
        except Exception:
            return ""

        return html_content.content.decode("utf-8")

    def parse_article_content(self, html_content: str, content_location: str = "p") -> str:
        soup = BeautifulSoup(html_content, features="html.parser")
        if html_content:
            content_text = [p.text.strip() for p in soup.findAll(content_location)]
            if replaced_str := "\xa0":
                content = [w.replace(replaced_str, " ") for w in content_text]
                return " ".join(content)
        return ""

    def collect(self, source):
        feed_url = source.parameter_values["FEED_URL"]
        # interval = source.parameter_values["REFRESH_INTERVAL"]

        logger.log_collector_activity("rss", source.id, f"Starting collector for url: {feed_url}")
        content_location = source.parameter_values.get("CONTENT_LOCATION", "p")

        if user_agent := source.parameter_values["USER_AGENT"]:
            self.headers = {"User-Agent": user_agent}

        try:
            self.rss_collector(feed_url, source, content_location)
        except Exception as error:
            logger.log_collector_activity("rss", source.id, "RSS collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            logger.log_debug(traceback.format_exc())

        logger.log_debug(f"{self.type} collection finished.")

    def content_from_feed(self, feed_entry, content_location) -> tuple[bool, str]:
        if content_location.startswith("xml_"):
            content_location = content_location.replace("xml_", "")
            if content_location in feed_entry:
                return True, content_location
            return False, content_location
        if "content" in feed_entry:
            content_location = "content"
            return True, content_location
        if "content:encoded" in feed_entry:
            content_location = "content:encoded"
            return True, content_location
        return False, content_location

    def rss_collector(self, feed_url, source, content_location):
        feed_content = self.make_request(feed_url)
        if not feed_content:
            logger.log_collector_activity("rss", source.id, "RSS returned no content")
            return
        feed = feedparser.parse(feed_content.content)

        logger.log_collector_activity("rss", source.id, f'RSS returned feed with {len(feed["entries"])} entries')

        news_items = []

        for feed_entry in feed["entries"]:

            for key in ["author", "published", "title", "description", "link"]:
                if key not in feed_entry:
                    feed_entry[key] = ""

            # limit = BaseCollector.history(interval)
            published = ""
            if "published" in feed_entry:
                try:
                    published = dateparser.parse(feed_entry["published"])
                except Exception:
                    published = feed_entry["published"]

            # if published > limit: TODO: uncomment after testing, we need some initial data now
            logger.log_collector_activity("rss", source.id, f"Processing entry [{feed_entry['link']}]")

            content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
            if content_from_feed:
                content = feed_entry[content_location]
            else:
                content = self.get_article_content(link_for_article=feed_entry["link"])
                content = self.parse_article_content(html_content=content, content_location=content_location)

            for_hash = feed_entry["author"] + feed_entry["title"] + feed_entry["link"]

            news_item = NewsItemData(
                uuid.uuid4(),
                hashlib.sha256(for_hash.encode()).hexdigest(),
                feed_entry["title"],
                feed_entry["description"],
                feed_url,
                feed_entry["link"],
                published,
                feed_entry["author"],
                datetime.datetime.now(),
                content,
                source.id,
                [],
            )

            news_items.append(news_item)

        self.publish(news_items, source)
