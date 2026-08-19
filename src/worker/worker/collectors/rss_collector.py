import datetime
import logging
from urllib.parse import urljoin, urlparse

import feedparser
import niquests as requests
from models.assess import NewsItem

from worker.collectors.base_web_collector import BaseWebCollector, parse_datetime
from worker.collectors.playwright_manager import PlaywrightManager
from worker.core_api import IconFile
from worker.log import logger


class RSSCollectorError(Exception):
    """Custom exception for RSSCollector errors."""

    def __init__(self, message: str = "Error parsing RSS feed"):
        super().__init__(message)
        logger.info(message)


class EmptyRSSFeedError(RSSCollectorError):
    def __init__(self, feed_url: str):
        self.feed_url = feed_url
        super().__init__(f"RSS feed {feed_url} returned no news items")


class RSSCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type: str = "RSS_COLLECTOR"
        self.name: str = "RSS Collector"
        self.description: str = "Collector for gathering data from RSS feeds"

        self.news_items: list[NewsItem] = []
        self.feed_url: str = ""
        self.feed_content: requests.Response
        self.language: str = ""
        self.use_feed_content: bool = False

        logger_trafilatura: logging.Logger = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def _determine_use_feed_content(self, params: dict) -> bool:
        use_feed_param = params.get("USE_FEED_CONTENT")

        if use_feed_param is not None:
            if isinstance(use_feed_param, bool):
                return use_feed_param
            if isinstance(use_feed_param, str):
                return use_feed_param.strip().lower() == "true"

        content_location = params.get("CONTENT_LOCATION")
        return bool(isinstance(content_location, str) and content_location.strip())

    def parse_source(self, source: dict):
        super().parse_source(source)
        params = source.get("parameters", {})

        self.feed_url = source["parameters"].get("FEED_URL", "")
        if not self.feed_url:
            raise ValueError("No FEED_URL set in source")

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

    def extract_content_from_feed(
        self,
        feed_entry: feedparser.FeedParserDict,
        source: dict,
    ) -> str:
        params = source.get("parameters", {})
        custom_location = params.get("CONTENT_LOCATION")

        locations: list[str] = []

        if isinstance(custom_location, str) and custom_location.strip():
            locations.append(custom_location.strip())

        locations += ["content", "content:encoded", "summary", "description"]

        for location in locations:
            if location not in feed_entry:
                continue

            value = feed_entry[location]

            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict) and "value" in first and (content := str(first["value"]).strip()):
                    return content

            if isinstance(value, str) and (content := value.strip()):
                return content

        return ""

    def get_published_date(self, feed_entry: feedparser.FeedParserDict) -> datetime.datetime | None:
        for field in ("published", "pubDate", "created", "updated", "modified", "dc:date"):
            if not (published := str(feed_entry.get(field) or "").strip()):
                continue
            if parsed := parse_datetime(published):
                return parsed

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
            content = self.extract_content_from_feed(feed_entry, source)

            if self.xpath and content and (extracted := self.xpath_extraction(content, self.xpath)):
                content = extracted
        elif link:
            web_content = self.extract_web_content(link, self.xpath)
            content = str(web_content.get("content"))
            author = author or str(web_content.get("author"))
            title = title or str(web_content.get("title"))
            validator_date = self.http_validators.get("last_modified") if self.http_validators else None
            published = published or web_content.get("published_date") or (parse_datetime(validator_date) if validator_date else None)

        else:
            logger.warning(f"No content could be extracted for RSS entry {feed_entry.get('id', link or title)}")

        if content == description:
            description = ""

        return NewsItem(
            osint_source_id=str(source["id"]),
            author=author,
            title=title,
            source=self.feed_url,
            content=content,
            link=link,
            published=published,
            language=self.language,
        )

    def update_favicon_from_feed(self, feed: feedparser.FeedParserDict, source_id: str):
        logger.info(f"RSS-Feed {self.feed_url} initial gather, get meta info about source like image icon and language")

        default_icon_url = f"{urlparse(self.feed_url).scheme}://{urlparse(self.feed_url).netloc}/favicon.ico"

        icon = feed.get("icon") or feed.get("image")

        icon_url = default_icon_url
        if possible_icon_url := RSSCollector.extract_icon_url(icon):
            icon_url = urljoin(self.feed_url, possible_icon_url)

        try:
            r = self._fetch_icon(icon_url)
            if not r.ok:
                logger.warning(f"Failed to fetch icon from {icon_url}, status: {r.status_code}")
                return

            content_type = (r.headers.get("content-type") or "").lower()
            if not content_type.startswith("image/"):
                logger.warning(f"URL {icon_url} did not return an image (content-type: {content_type})")
                return
            if not (content := r.content):
                logger.warning(f"URL {icon_url} returned no content")
                return

            parsed = urlparse(icon_url)
            filename = parsed.path.rsplit("/", 1)[-1] or "favicon.ico"
            icon_content: IconFile = {"file": (filename, content)}

            self.core_api.update_osint_source_icon(source_id, icon_content)

        except (ValueError, requests.exceptions.RequestException) as e:
            logger.error(f"Exception while fetching icon from {icon_url}: {e}")

        return

    def parse_feed(self, feed_entries: list[feedparser.FeedParserDict], source: dict) -> list[NewsItem]:
        for feed_entry in feed_entries:
            self.news_items.append(self.parse_feed_entry(feed_entry, source))
        return self.news_items

    def gather_news_items(self, feed: feedparser.FeedParserDict, source: dict) -> list[NewsItem]:
        if self.browser_mode == "true":
            self.playwright_manager = PlaywrightManager(self.proxies, self._request_headers(""))
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

    def get_feed(self) -> feedparser.FeedParserDict:
        """Send GET request to URL of RSS feed."""

        self.feed_content = self.send_get_request(self.feed_url)

        feed = feedparser.parse(self.feed_content.content)
        if not feed.get("version"):
            parser_error = feed.get("bozo_exception")
            error_detail = f": {parser_error}" if parser_error else ""
            raise RSSCollectorError(f"No parseable RSS or Atom feed was detected at {self.feed_url}{error_detail}")
        return feed

    def preview_collector(self, source: dict):
        self.parse_source(source)
        self.configure_primary_http_resource(source, self.feed_url, manual=True)
        feed = self.get_feed()
        self.news_items = self.gather_news_items(feed, source)
        return self.preview(self.news_items, source)

    def rss_collector(self, source: dict, manual: bool = False):
        self.last_attempted = self.get_last_attempted(source)
        self.configure_primary_http_resource(source, self.feed_url, manual=manual)
        feed = self.get_feed()
        self.language = feed.feed.get("language", feed.feed.get("lang", ""))  # type: ignore

        if not self.last_attempted and not source.get("http_validators"):
            self.update_favicon_from_feed(feed.feed, source["id"])  # type: ignore

        logger.info(f"RSS-Feed {self.feed_url} returned feed with {len(feed['entries'])} entries")

        if not feed["entries"]:
            raise EmptyRSSFeedError(self.feed_url)
        self.news_items = self.gather_news_items(feed, source)

        return self.publish(self.news_items, source)
