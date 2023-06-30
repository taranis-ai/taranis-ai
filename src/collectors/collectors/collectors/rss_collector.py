import datetime
import hashlib
import uuid
import feedparser
import requests
from bs4 import BeautifulSoup
import dateutil.parser as dateparser
from trafilatura import extract

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
        response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response.ok:
            raise RuntimeError(f"Response not ok: {response.status_code}")
        return response

    def get_article_content(self, link_for_article: str) -> str:
        html_content = self.make_request(link_for_article)

        return html_content.content.decode("utf-8") if html_content is not None else ""

    def parse_article_content(self, html_content: str, content_location: str | None) -> str:
        if not html_content:
            return ""

        if not content_location:
            content = extract(html_content, include_links=False, include_comments=False, include_formatting=False, with_metadata=False)
            return content or html_content

        soup = BeautifulSoup(html_content, features="html.parser")
        content_text = [p.text.strip() for p in soup.findAll(content_location)]
        return " ".join([w.replace("\xa0", " ") for w in content_text])

    def collect(self, source):
        feed_url = source["parameter_values"].get("FEED_URL", None)
        if not feed_url:
            logger.warning("No FEED_URL set")
            return "No FEED_URL set"

        logger.log_collector_activity("rss", source["id"], f"Starting collector for url: {feed_url}")

        if user_agent := source["parameter_values"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

        try:
            self.rss_collector(feed_url, source)
        except Exception as e:
            logger.exception()
            return str(e)

        logger.log_debug(f"{self.type} collection finished.")
        return None

    def content_from_feed(self, feed_entry, content_location: str) -> tuple[bool, str]:
        content_locations = [content_location, "content", "content:encoded"]
        for location in content_locations:
            if location in feed_entry and isinstance(feed_entry[location], str):
                return True, location
        return False, content_location

    def get_published_date(self, feed_entry: feedparser.FeedParserDict) -> datetime.datetime:
        published: str | datetime.datetime = str(feed_entry.get("published")) or str(feed_entry.get("pubDate")) or ""
        if not published:
            link: str = str(feed_entry.get("link", ""))
            if not link:
                return datetime.datetime.now()
            response = requests.head(link, headers=self.headers, proxies=self.proxies)
            if not response.ok:
                return datetime.datetime.now()

            published = str(response.headers.get("Last-Modified", ""))
        try:
            return dateparser.parse(published) if published else datetime.datetime.now()
        except Exception:
            return datetime.datetime.now()

    def parse_feed(self, feed_entry: feedparser.FeedParserDict, feed_url: str, source) -> NewsItemData:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))
        for_hash: str = author + title + link

        published = self.get_published_date(feed_entry)

        # if published > limit: TODO: uncomment after testing, we need some initial data now
        logger.log_collector_activity("rss", source["id"], f"Processing entry [{link}]")

        content_location = source["parameter_values"].get("CONTENT_LOCATION", None)
        content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
        if content_from_feed:
            content = str(feed_entry[content_location])
        else:
            html_content = self.get_article_content(link_for_article=link)
            content = self.parse_article_content(html_content, content_location)

        return NewsItemData(
            uuid.uuid4(),
            hashlib.sha256(for_hash.encode()).hexdigest(),
            title,
            description,
            feed_url,
            link,
            published,
            author,
            datetime.datetime.now(),
            content,
            source["id"],
            [],
        )

    def rss_collector(self, feed_url: str, source):
        feed_content = self.make_request(feed_url)
        if not feed_content:
            logger.log_collector_activity("rss", source['id'], "RSS returned no content")
            raise ValueError("RSS returned no content")
        feed = feedparser.parse(feed_content.content)

        logger.log_collector_activity("rss", source["id"], f'RSS returned feed with {len(feed["entries"])} entries')

        news_items = [self.parse_feed(feed_entry, feed_url, source) for feed_entry in feed["entries"][:100]]

        self.publish(news_items, source)
