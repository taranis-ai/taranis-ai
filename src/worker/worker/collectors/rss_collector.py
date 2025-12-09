import datetime
import hashlib
import feedparser
import requests
import logging
from urllib.parse import urljoin, urlparse
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
        self.type: str = "RSS_COLLECTOR"
        self.name: str = "RSS Collector"
        self.description: str = "Collector for gathering data from RSS feeds"

        self.news_items: list[NewsItem] = []
        self.timeout: int = 60
        self.feed_url: str = ""
        self.feed_content: requests.Response
        self.last_modified: datetime.datetime | None = None
        self.last_attempted: datetime.datetime | None = None
        self.language: str = ""
        self.use_feed_content: bool = False

        logger_trafilatura: logging.Logger = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def _determine_use_feed_content(self, params: dict) -> bool:
        use_feed_param = params.get("USE_FEED_CONTENT")
        legacy_param = params.get("CONTENT_LOCATION")

        if isinstance(use_feed_param, str):
            return use_feed_param.strip().lower() == "true"
        if isinstance(use_feed_param, bool):
            return use_feed_param
        if isinstance(legacy_param, str):
            return legacy_param.strip().lower() == "feed"
        return False

    def parse_source(self, source: dict):
        super().parse_source(source)
        params = source.get("parameters", {})

        self.feed_url = source["parameters"].get("FEED_URL", "")
        if not self.feed_url:
            raise ValueError("No FEED_URL set in source")

        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))
        self.use_feed_content = self._determine_use_feed_content(params)

    def collect(self, source: dict, manual: bool = False):
        self.parse_source(source)
        return self.rss_collector(source, manual)

    @staticmethod
    def extract_icon_url(icon) -> str | None:
        def from_mapping(m) -> str | None:
            href = m.get("href") or m.get("url")
            if isinstance(href, str) and href.strip():
                return href.strip()
            if isinstance(href, list):
                for item in href:
                    if isinstance(item, str) and item.strip():
                        return item.strip()
            return None

        if isinstance(icon, (feedparser.FeedParserDict, dict)):
            return from_mapping(icon)

        if isinstance(icon, str):
            return icon.strip() or None

        if isinstance(icon, list):
            for item in icon:
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, (feedparser.FeedParserDict, dict)):
                    url = from_mapping(item)
                    if url:
                        return url
            return None

        return None

    def extract_content_from_feed(self, feed_entry: feedparser.FeedParserDict) -> str:
        content_locations = ["content", "content:encoded", "summary", "description"]
        for location in content_locations:
            if location not in feed_entry:
                continue
            value = feed_entry[location]
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict) and "value" in first:
                    return str(first["value"])
            if isinstance(value, str):
                return value
        return ""


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
            logger.info("Could not parse published date from feed")
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

        if link_transformer := source["parameters"].get("LINK_TRANSFORMER", None):
            link = self.link_transformer(link, link_transformer)

        published = self.get_published_date(feed_entry)
        content = ""

        if self.use_feed_content:
            content = self.extract_content_from_feed(feed_entry)

            if self.xpath and content:
                if extracted := self.xpath_extraction(content, self.xpath):
                    content = extracted
        elif link:
            web_content = self.extract_web_content(link, self.xpath)
            content = str(web_content.get("content"))
            author = author or str(web_content.get("author"))
            title = title or str(web_content.get("title"))
            published = published or web_content.get("published_date") or self.last_modified

        else:
            logger.warning("No content could be extracted for RSS entry %r", feed_entry.get("id", link or title))

        if content == description:
            description = ""

        for_hash: str = title + self.clean_url(link)

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

        default_icon_url = f"{urlparse(self.feed_url).scheme}://{urlparse(self.feed_url).netloc}/favicon.ico"

        icon = feed.get("icon") or feed.get("image")

        icon_url = default_icon_url
        if possible_icon_url := RSSCollector.extract_icon_url(icon):
            icon_url = urljoin(self.feed_url, possible_icon_url)

        try:
            r = requests.get(icon_url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            if not r.ok:
                logger.warning(f"Failed to fetch icon from {icon_url}, status: {r.status_code}")
                return None

            content_type = (r.headers.get("content-type") or "").lower()
            if not content_type.startswith("image/"):
                logger.warning(f"URL {icon_url} did not return an image (content-type: {content_type})")
                return None

            parsed = urlparse(icon_url)
            filename = parsed.path.rsplit("/", 1)[-1] or "favicon.ico"
            icon_content = {"file": (filename, r.content)}

            self.core_api.update_osint_source_icon(source_id, icon_content)

        except Exception as e:
            logger.error(f"Exception while fetching icon from {icon_url}: {e}")

        return None

    def parse_feed(self, feed_entries: list[feedparser.FeedParserDict], source: dict) -> list[NewsItem]:
        for feed_entry in feed_entries:
            try:
                self.news_items.append(self.parse_feed_entry(feed_entry, source))
            except Exception as e:
                logger.warning(f"Error parsing feed entry: {str(e)}")
                continue
        return self.news_items

    def gather_news_items(self, feed: feedparser.FeedParserDict, source: dict) -> list[NewsItem]:
        if self.browser_mode == "true":
            self.playwright_manager = PlaywrightManager(self.proxies, self.headers)
        try:
            self.news_items = self.collect_news(feed, source)
        finally:
            if self.playwright_manager:
                self.playwright_manager.stop_playwright_if_needed()

            return self.news_items

    def collect_news(self, feed: feedparser.FeedParserDict, source: dict) -> list[NewsItem]:
        if self.digest_splitting == "true":
            return self.handle_digests(feed["entries"][:42])

        return self.parse_feed(feed["entries"][:42], source)

    def handle_digests(self, feed_entries: list[feedparser.FeedParserDict]) -> list[NewsItem]:
        self.split_digest_urls = self.get_digest_url_list(feed_entries)
        logger.info(f"RSS-Feed {self.feed_url} returned {len(self.split_digest_urls)} available URLs")

        return self.parse_digests()

    def get_digest_url_list(self, feed_entries: list[feedparser.FeedParserDict]) -> list:
        return [
            result
            for feed_entry in feed_entries
            for result in self.get_urls(self.feed_url, feed_entry.get("summary"))  # type: ignore
        ]  # Flat list of URLs

    def get_feed(self, manual: bool = False) -> feedparser.FeedParserDict:
        """Send GET request to URL of RSS feed."""

        # if manual flag is set, ignore if the feed was not modified
        modified_since = None if manual else self.last_attempted
        self.feed_content = self.send_get_request(self.feed_url, modified_since)

        return feedparser.parse(self.feed_content.content)

    def preview_collector(self, source: dict):
        self.parse_source(source)
        feed = self.get_feed(manual=True)
        self.news_items = self.gather_news_items(feed, source)
        return self.preview(self.news_items, source)

    def rss_collector(self, source: dict, manual: bool = False):
        self.last_attempted = self.get_last_attempted(source)
        feed = self.get_feed(manual)
        self.language = self.extract_language(feed.feed)

        if not self.last_attempted:
            self.update_favicon_from_feed(feed.feed, source["id"])  # type: ignore
        self.last_modified = self.get_last_modified_feed(self.feed_content, feed)
        if self.last_modified and self.last_attempted and self.last_modified < self.last_attempted and not manual:
            raise NoChangeError(f"Last-Modified: {self.last_modified} < Last-Attempted {self.last_attempted} skipping")

        logger.info(f"RSS-Feed {self.feed_url} returned feed with {len(feed['entries'])} entries")

        self.news_items = self.gather_news_items(feed, source)

        return self.publish(self.news_items, source)

    @staticmethod
    def extract_language(feed_meta: feedparser.FeedParserDict) -> str:
        raw = feed_meta.get("language") or feed_meta.get("lang")

        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if not isinstance(raw, str):
            return ""

        raw = raw.strip()
        return raw or ""
