import datetime
import hashlib
import uuid
import feedparser
import requests
import logging
from urllib.parse import urlparse
import dateutil.parser as dateparser
from trafilatura import extract

from worker.collectors.base_web_collector import BaseWebCollector
from worker.log import logger


class RSSCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "RSS_COLLECTOR"
        self.name = "RSS Collector"
        self.description = "Collector for gathering data from RSS feeds"

        self.news_items = []
        self.headers = {}
        self.timeout = 60
        self.feed_url = ""
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def parse_source(self, source):
        self.feed_url = source["parameters"].get("FEED_URL")
        if not self.feed_url:
            logger.warning("No FEED_URL set")
            return {"error": "No FEED_URL set"}

        self.set_proxies(source["parameters"].get("PROXY_SERVER", None))

        logger.info(f"RSS-Feed {source['id']} Starting collector for url: {self.feed_url}")

        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

    def collect(self, source):
        self.parse_source(source)
        try:
            return self.rss_collector(source)
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

    def get_published_date(self, feed_entry: feedparser.FeedParserDict, link: str, collected: datetime.datetime) -> datetime.datetime:
        published: str | datetime.datetime = str(
            feed_entry.get(
                "published",
                feed_entry.get(
                    "pubDate", feed_entry.get("created", feed_entry.get("updated", feed_entry.get("modified", feed_entry.get("dc:date", ""))))
                ),
            )
        )
        if not published:
            if not link:
                return self.last_modified or collected
            response = requests.head(link, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            if not response.ok:
                return self.last_modified or collected

            published = str(response.headers.get("Last-Modified", ""))
        try:
            return dateparser.parse(published, ignoretz=True) if published else collected
        except Exception:
            logger.info("Could not parse date - falling back to current date")
            return self.last_modified or collected

    def link_transformer(self, link: str, transform_str: str) -> str:
        parsed_url = urlparse(link)
        segments = [parsed_url.netloc] + parsed_url.path.strip("/").split("/")
        transformed_segments = [operation.replace("{}", segment) for segment, operation in zip(segments, transform_str.split("/"))]
        return f"{parsed_url.scheme}://{'/'.join(transformed_segments)}"

    def get_article_content(self, link_for_article: str) -> str:
        html_content = self.make_request(link_for_article)

        return html_content.content.decode("utf-8") if html_content is not None else ""

    def content_from_article(self, url: str, xpath: str | None) -> str:
        html_content = self.get_article_content(url)
        if not xpath:
            content = extract(html_content, include_links=False, include_comments=False, include_formatting=False, with_metadata=False)
            return content or html_content

        return self.xpath_extraction(html_content, xpath)

    def parse_feed(self, feed_entry: feedparser.FeedParserDict, source) -> dict[str, str | datetime.datetime | list]:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))
        collected: datetime.datetime = datetime.datetime.now()
        for_hash: str = author + title + link

        if "redteam-pentesting.de" in link:  # TODO: Remove this once the the source schema is updated
            source["parameters"]["LINK_TRANSFORMER"] = "{}/{}/{}/{}.txt"

        if link_transformer := source["parameters"].get("LINK_TRANSFORMER", None):
            link = self.link_transformer(link, link_transformer)

        published = self.get_published_date(feed_entry, link, collected)

        content_location = source["parameters"].get("CONTENT_LOCATION", None)
        content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
        if content_from_feed:
            content = str(feed_entry[content_location])
        elif link:
            if published.date() >= (datetime.date.today() - datetime.timedelta(days=90)):
                xpath = source["parameters"].get("XPATH", None)
                content = self.content_from_article(link, xpath)
            else:
                content = "The article is older than 90 days - skipping"
        elif description:
            content = description
        else:
            content = "No content found in feed or article - please check your CONTENT_LOCATION parameter"

        if content == description:
            description = ""

        return {
            "id": str(uuid.uuid4()),
            "hash": hashlib.sha256(for_hash.encode()).hexdigest(),
            "title": title,
            "review": description,
            "source": self.feed_url,
            "link": link,
            "published": published,
            "author": author,
            "collected": collected,
            "content": content,
            "osint_source_id": source["id"],
            "attributes": [],
        }

    def get_last_modified(self, feed_content: requests.Response, feed: feedparser.FeedParserDict) -> datetime.datetime | None:
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

    def get_feed(self) -> feedparser.FeedParserDict:
        self.feed_content = self.make_request(self.feed_url)
        if not self.feed_content:
            logger.info(f"RSS-Feed {self.feed_url} returned no content")
            raise ValueError("RSS returned no content")
        return feedparser.parse(self.feed_content.content)

    def preview_collector(self, source):
        self.parse_source(source)
        feed = self.get_feed()
        news_items = [self.parse_feed(feed_entry, source) for feed_entry in feed["entries"][:42]]

        return self.preview(news_items, source)

    def rss_collector(self, source):
        feed = self.get_feed()

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(feed.feed, source["id"])
        last_modified = self.get_last_modified(self.feed_content, feed)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        logger.info(f"RSS-Feed {source['id']} returned feed with {len(feed['entries'])} entries")

        news_items = [self.parse_feed(feed_entry, source) for feed_entry in feed["entries"][:42]]

        self.publish(news_items, source)
        return None
