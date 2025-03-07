import datetime
import hashlib
import feedparser
import requests
import logging
from urllib.parse import urlparse
import dateutil.parser as dateparser

from worker.collectors.base_web_collector import BaseWebCollector, NoChangeError
from worker.collectors.playwright_manager import PlaywrightManager
from worker.log import logger
from worker.types import NewsItem


class RSSCollectorError(Exception):
    """Custom exception for RSSCollector errors."""

    def __init__(self, message="Error parsing RSS feed"):
        super().__init__(message)
        logger.info(message)


class RSSCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "RSS_COLLECTOR"
        self.name = "RSS Collector"
        self.description = "Collector for gathering data from RSS feeds"

        self.news_items: list[NewsItem] = []
        self.timeout = 60
        self.feed_url = ""
        self.feed_content: requests.Response
        self.last_modified = None
        self.last_attempted = None
        self.language = None

        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        super().parse_source(source)
        self.feed_url = source["parameters"].get("FEED_URL")
        if not self.feed_url:
            logger.error("No FEED_URL set")
            raise ValueError("No FEED_URL set")

        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))

    def collect(self, source, manual: bool = False):
        self.parse_source(source)
        try:
            return self.rss_collector(source, manual)
        except Exception as e:
            logger.exception(f"RSS collector failed with error: {str(e)}")
            return str(e)

    def content_from_feed(self, feed_entry, content_location: str) -> tuple[bool, str]:
        content_locations = [content_location, "content", "content:encoded"]
        for location in content_locations:
            if location in feed_entry and isinstance(feed_entry[location], str):
                return True, location
        return False, content_location

    def get_published_date(self, feed_entry: feedparser.FeedParserDict) -> datetime.datetime | None:
        published: str | datetime.datetime = str(
            feed_entry.get(
                "published",
                feed_entry.get(
                    "pubDate", feed_entry.get("created", feed_entry.get("updated", feed_entry.get("modified", feed_entry.get("dc:date", ""))))
                ),
            )
        )
        try:
            return dateparser.parse(published, ignoretz=True) if published else None
        except Exception:
            logger.info("Could not parse date - falling back to current date")
            return None

    def link_transformer(self, link: str, transform_str: str = "") -> str:
        parsed_url = urlparse(link)
        segments = [parsed_url.netloc] + parsed_url.path.strip("/").split("/")
        transformed_segments = [operation.replace("{}", segment) for segment, operation in zip(segments, transform_str.split("/"))]
        return f"{parsed_url.scheme}://{'/'.join(transformed_segments)}"

    def parse_feed_entry(self, feed_entry: feedparser.FeedParserDict, source) -> NewsItem:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))
        content: str = ""

        if link_transformer := source["parameters"].get("LINK_TRANSFORMER", None):
            link = self.link_transformer(link, link_transformer)

        published = self.get_published_date(feed_entry)

        content_location = source["parameters"].get("CONTENT_LOCATION", None)
        content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
        if content_from_feed:
            content = str(feed_entry[content_location])
        if link:
            web_content = self.extract_web_content(link, self.xpath)
            content = content if content_from_feed else str(web_content.get("content"))
            author = author or str(web_content.get("author"))
            title = title or str(web_content.get("title"))
            published = published or web_content.get("published_date") or self.last_modified

        if content == description:
            description = ""

        for_hash: str = author + title + self.clean_url(link)

        return NewsItem(
            osint_source_id=source["id"],
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            source=self.feed_url,
            content=content,
            web_url=link,
            published_date=published,
            language=self.language,
        )

    # TODO: This function is renamed because of inheritance issues.
    def get_last_modified_feed(self, feed_content: requests.Response, feed: feedparser.FeedParserDict) -> datetime.datetime | None:
        if last_modified := feed_content.headers.get("Last-Modified"):
            return dateparser.parse(last_modified, ignoretz=True)
        elif last_modified := feed.get(
            "updated", feed.get("modified", feed.get("created", feed.get("pubDate", feed.get("lastBuildDate", None))))
        ):
            try:
                return dateparser.parse(str(last_modified), ignoretz=True)
            except Exception:
                return None
        return None

    def update_favicon_from_feed(self, feed: feedparser.FeedParserDict, source_id: str):
        logger.info(f"RSS-Feed {self.feed_url} initial gather, get meta info about source like image icon and language")
        icon_url = f"{urlparse(self.feed_url).scheme}://{urlparse(self.feed_url).netloc}/favicon.ico"
        icon = feed.get("icon", feed.get("image"))
        if isinstance(icon, feedparser.FeedParserDict):
            icon_url = str(icon.get("href"))
        elif isinstance(icon, str):
            icon_url = str(icon)
        elif isinstance(icon, list):
            icon_url = str(icon[0].get("href"))
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
        if not r.ok:
            return None

        if "image" not in r.headers.get("content-type", ""):
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(source_id, icon_content)
        return None

    def parse_feed(self, feed_entries: list[feedparser.FeedParserDict], source) -> list[NewsItem]:
        for feed_entry in feed_entries:
            try:
                self.news_items.append(self.parse_feed_entry(feed_entry, source))
            except Exception as e:
                logger.warning(f"Error parsing feed entry: {str(e)}")
                continue
        return self.news_items

    def gather_news_items(self, feed, source) -> list[NewsItem]:
        if self.browser_mode == "true":
            self.playwright_manager = PlaywrightManager(self.proxies, self.headers)
        try:
            self.news_items = self.collect_news(feed, source)
        finally:
            if self.playwright_manager:
                self.playwright_manager.stop_playwright_if_needed()

            return self.news_items

    def collect_news(self, feed, source) -> list[NewsItem]:
        if self.digest_splitting == "true":
            return self.handle_digests(feed["entries"][:42])

        return self.parse_feed(feed["entries"][:42], source)

    def handle_digests(self, feed_entries: list[feedparser.FeedParserDict]) -> list[NewsItem]:
        self.split_digest_urls = self.get_digest_url_list(feed_entries)
        logger.info(f"RSS-Feed {self.osint_source_id} returned {len(self.split_digest_urls)} available URLs")

        return self.parse_digests()

    def get_digest_url_list(self, feed_entries) -> list:
        return [
            result for feed_entry in feed_entries for result in self.get_urls(self.feed_url, feed_entry.get("summary"))
        ]  # Flat list of URLs

    def get_feed(self, manual: bool = False) -> feedparser.FeedParserDict:
        """Send GET request to URL of RSS feed."""

        # if manual flag is set, ignore if the feed was not modified
        modified_since = None if manual else self.last_attempted
        self.feed_content = self.send_get_request(self.feed_url, modified_since)

        return feedparser.parse(self.feed_content.content)

    def preview_collector(self, source):
        self.parse_source(source)
        feed = self.get_feed(manual=True)
        self.news_items = self.gather_news_items(feed, source)
        return self.preview(self.news_items, source)

    def rss_collector(self, source, manual: bool = False):
        self.last_attempted = self.get_last_attempted(source)
        feed = self.get_feed(manual)

        if not self.last_attempted:
            self.update_favicon_from_feed(feed.feed, source["id"])  # type: ignore
        self.last_modified = self.get_last_modified_feed(self.feed_content, feed)
        if self.last_modified and self.last_attempted and self.last_modified < self.last_attempted and not manual:
            raise NoChangeError(f"Last-Modified: {self.last_modified} < Last-Attempted {self.last_attempted} skipping")

        logger.info(f"RSS-Feed {source['id']} returned feed with {len(feed['entries'])} entries")

        self.news_items = self.gather_news_items(feed, source)

        self.publish(self.news_items, source)
        return None

    def detect_language_from_feed(self, feed: dict):
        if language := feed.get("feed", {}).get("language"):
            self.language = language
