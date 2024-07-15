import datetime
import hashlib
import feedparser
import requests
import logging
from urllib.parse import urlparse
import dateutil.parser as dateparser
from trafilatura import extract

from worker.collectors.base_web_collector import BaseWebCollector
from worker.log import logger
from worker.types import NewsItem


class RSSCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "RSS_COLLECTOR"
        self.name = "RSS Collector"
        self.description = "Collector for gathering data from RSS feeds"

        self.news_items = []
        self.timeout = 60
        self.feed_url = ""
        self.feed_content = None
        self.last_modified = None
        self.digest_splitting_limit = None
        self.split_digest_urls = []
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        super().parse_source(source)
        self.feed_url = source["parameters"].get("FEED_URL")
        if not self.feed_url:
            logger.warning("No FEED_URL set")
            return {"error": "No FEED_URL set"}

        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))

    def collect(self, source, manual: bool = False):
        self.parse_source(source)
        try:
            return self.rss_collector(source, manual)
        except Exception as e:
            logger.exception()
            logger.error(f"RSS collector failed with error: {str(e)}")
            return str(e)

    def make_request(self, url: str) -> None | requests.Response:
        response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
        if not response.ok:
            raise RuntimeError(f"Response not ok: {response.status_code}")
        return response

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

    def get_article_content(self, link_for_article: str) -> str:
        return self.make_request(link_for_article) or ""

    def content_from_article(self, url: str, xpath: str | None) -> str:
        html_content = self.get_article_content(url)
        if not xpath:
            content = extract(html_content, include_links=False, include_comments=False, include_formatting=False, with_metadata=False)
            return content or html_content

        return self.xpath_extraction(html_content, xpath)

    def parse_feed_entry(self, feed_entry: feedparser.FeedParserDict, source) -> NewsItem:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))

        if link_transformer := source["parameters"].get("LINK_TRANSFORMER", None):
            link = self.link_transformer(link, link_transformer)

        published = self.get_published_date(feed_entry)

        content_location = source["parameters"].get("CONTENT_LOCATION", None)
        content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
        if content_from_feed:
            content = str(feed_entry[content_location])
        if link:
            web_content = self.parse_web_content(link, source["parameters"].get("XPATH", None))
            content = content if content_from_feed else web_content.get("content")
            author = author or web_content.get("author")
            title = title or web_content.get("title")
            published = published or web_content.get("published_date") or self.last_modified

        if content == description:
            description = ""

        for_hash: str = author + title + self.clean_url(link)

        return NewsItem(
            osint_source_id=source["id"],
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            content=content,
            web_url=link,
            published_date=published,
            language=source.get("language", ""),
            review=source.get("review", ""),
        )

    # TODO: This function is renamed because of inheritance issues. Notice that @feed is/was not used in the function.
    def get_last_modified_feed(self, feed_content: requests.Response, feed: feedparser.FeedParserDict) -> datetime.datetime | None:
        feed = feedparser.parse(feed_content.content)
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

    def update_favicon(self, feed: feedparser.FeedParserDict, source_id: str):
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

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(source_id, icon_content)
        return None

    def parse_feed(self, feed_entries: list[feedparser.FeedParserDict], source) -> list[NewsItem]:
        news_items = []
        for feed_entry in feed_entries:
            try:
                news_items.append(self.parse_feed_entry(feed_entry, source))
            except Exception as e:
                logger.warning(f"Error parsing feed entry: {str(e)}")
                continue
        return news_items

    def get_digest_url_list(self, feed_entries) -> list:
        return [result for feed_entry in feed_entries for result in self.get_urls(feed_entry.get("summary"))]  # Flat list of URLs

    def get_news_items(self, feed, source) -> list | str:
        digest_splitting = source["parameters"].get("DIGEST_SPLITTING", False)
        if digest_splitting == "true":
            return self.handle_digests(feed["entries"][:42])

        return self.parse_feed(feed["entries"][:42], source)

    def handle_digests(self, feed_entries: list[feedparser.FeedParserDict]) -> list[dict] | str:
        self.split_digest_urls = self.get_digest_url_list(feed_entries)
        logger.info(f"RSS-Feed {self.osint_source_id} returned {len(self.split_digest_urls)} available URLs")

        return self.parse_digests()

    def get_feed(self) -> feedparser.FeedParserDict:
        self.feed_content = self.make_request(self.feed_url)
        if not self.feed_content:
            logger.info(f"RSS-Feed {self.feed_url} returned no content")
            raise ValueError("RSS returned no content")
        return feedparser.parse(self.feed_content.content)

    def preview_collector(self, source):
        self.parse_source(source)
        feed = self.get_feed()
        news_items = self.get_news_items(feed, source)
        return self.preview(news_items, source)

    def rss_collector(self, source, manual: bool = False):
        feed = self.get_feed()

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(feed.feed, source["id"])
        last_modified = self.get_last_modified_feed(self.feed_content, feed)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted and not manual:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        logger.info(f"RSS-Feed {source['id']} returned feed with {len(feed['entries'])} entries")

        self.news_items = self.get_news_items(feed, source)

        self.publish(self.news_items, source)
        return None
