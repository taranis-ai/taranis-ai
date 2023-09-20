import datetime
import hashlib
import uuid
import feedparser
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import dateutil.parser as dateparser
from trafilatura import extract

from .base_collector import BaseCollector
from worker.log import logger


class RSSCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "RSS_COLLECTOR"
        self.name = "RSS Collector"
        self.description = "Collector for gathering data from RSS feeds"

        self.news_items = []
        self.proxies = None
        self.headers = {}
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def collect(self, source):
        feed_url = source["parameters"].get("FEED_URL", None)
        if not feed_url:
            logger.warning("No FEED_URL set")
            return "No FEED_URL set"

        logger.info(f"RSS-Feed {source['id']} Starting collector for url: {feed_url}")

        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

        try:
            return self.rss_collector(feed_url, source)
        except Exception as e:
            logger.exception()
            logger.error(f"RSS collector for {feed_url} failed with error: {str(e)}")
            return str(e)

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

    def content_from_feed(self, feed_entry, content_location: str) -> tuple[bool, str]:
        content_locations = [content_location, "content", "content:encoded"]
        for location in content_locations:
            if location in feed_entry and isinstance(feed_entry[location], str):
                return True, location
        return False, content_location

    def get_published_date(self, feed_entry: feedparser.FeedParserDict, link: str) -> datetime.datetime:
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
                return self.last_modified or datetime.datetime.now()
            response = requests.head(link, headers=self.headers, proxies=self.proxies)
            if not response.ok:
                return self.last_modified or datetime.datetime.now()

            published = str(response.headers.get("Last-Modified", ""))
        try:
            return dateparser.parse(published, ignoretz=True) if published else datetime.datetime.now()
        except Exception:
            logger.info("Could not parse date - falling back to current date")
            return self.last_modified or datetime.datetime.now()

    def link_transformer(self, link: str, transform_str: str) -> str:
        parsed_url = urlparse(link)
        segments = [parsed_url.netloc] + parsed_url.path.strip("/").split("/")
        transformed_segments = [operation.replace("{}", segment) for segment, operation in zip(segments, transform_str.split("/"))]
        return f"{parsed_url.scheme}://{'/'.join(transformed_segments)}"

    def parse_feed(self, feed_entry: feedparser.FeedParserDict, feed_url, source) -> dict[str, str | datetime.datetime | list]:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))
        for_hash: str = author + title + link

        if "redteam-pentesting.de" in link:  # TODO: Remove this once the the source schema is updated
            source["parameters"]["LINK_TRANSFORMER"] = "{}/{}/{}/{}.txt"

        if link_transformer := source["parameters"].get("LINK_TRANSFORMER", None):
            link = self.link_transformer(link, link_transformer)

        published = self.get_published_date(feed_entry, link)

        content_location = source["parameters"].get("CONTENT_LOCATION", None)
        content_from_feed, content_location = self.content_from_feed(feed_entry, content_location)
        if content_from_feed:
            content = str(feed_entry[content_location])
        elif link:
            if published.date() >= (datetime.date.today() - datetime.timedelta(days=90)):
                html_content = self.get_article_content(link_for_article=link)
                content = self.parse_article_content(html_content, content_location)
            else:
                content = "The article is older than 90 days - skipping"
        elif description:
            content = description
        else:
            content = "No content found in feed or article - please check your CONTENT_LOCATION parameter"

        return {
            "id": str(uuid.uuid4()),
            "hash": hashlib.sha256(for_hash.encode()).hexdigest(),
            "title": title,
            "review": description,
            "source": feed_url,
            "link": link,
            "published": published,
            "author": author,
            "collected": datetime.datetime.now(),
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

    def get_last_attempted(self, source: dict) -> datetime.datetime | None:
        if last_attempted := source.get("last_attempted"):
            try:
                return dateparser.parse(last_attempted, ignoretz=True)
            except Exception:
                return None
        return None

    def initial_gather(self, feed: feedparser.FeedParserDict, feed_url: str, source_id: str):
        logger.info(f"RSS-Feed {feed_url} initial gather, get meta info about source like image icon and language")
        icon_url = f"{urlparse(feed_url).scheme}://{urlparse(feed_url).netloc}/favicon.ico"
        if icon := feed.get("icon", feed.get("image")):
            if type(icon) == feedparser.FeedParserDict:
                icon_url = str(icon.get("href"))
            elif type(icon) == str:
                icon_url = str(icon)
            elif type(icon) == list:
                icon_url = str(icon[0].get("href"))
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies)
        if not r.ok:
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(source_id, icon_content)
        return None

    def rss_collector(self, feed_url: str, source):
        feed_content = self.make_request(feed_url)
        if not feed_content:
            logger.info(f"RSS-Feed {source['id']} returned no content")
            raise ValueError("RSS returned no content")

        feed = feedparser.parse(feed_content.content)

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.initial_gather(feed.feed, feed_url, source["id"])
        last_modified = self.get_last_modified(feed_content, feed)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        logger.info(f"RSS-Feed {source['id']} returned feed with {len(feed['entries'])} entries")

        news_items = [self.parse_feed(feed_entry, feed_url, source) for feed_entry in feed["entries"][:42]]

        self.publish(news_items, source)
        return None
