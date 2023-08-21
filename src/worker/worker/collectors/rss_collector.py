import datetime
import hashlib
import uuid
import feedparser
import requests
import logging
from bs4 import BeautifulSoup
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
        feed_url = source["parameter_values"].get("FEED_URL", None)
        if not feed_url:
            logger.warning("No FEED_URL set")
            return "No FEED_URL set"

        logger.info(f"RSS-Feed {source['id']} Starting collector for url: {feed_url}")

        if user_agent := source["parameter_values"].get("USER_AGENT", None):
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

    def get_published_date(self, feed_entry: feedparser.FeedParserDict) -> datetime.datetime:
        published: str | datetime.datetime = str(
            feed_entry.get(
                "published",
                feed_entry.get(
                    "pubDate", feed_entry.get("created", feed_entry.get("updated", feed_entry.get("modified", feed_entry.get("dc:date", ""))))
                ),
            )
        )
        if not published:
            link: str = str(feed_entry.get("link", ""))
            if not link:
                return datetime.datetime.now()
            response = requests.head(link, headers=self.headers, proxies=self.proxies)
            if not response.ok:
                return datetime.datetime.now()

            published = str(response.headers.get("Last-Modified", ""))
        try:
            return dateparser.parse(published, ignoretz=True) if published else datetime.datetime.now()
        except Exception:
            logger.info("Could not parse date - falling back to current date")
            return datetime.datetime.now()

    def parse_feed(self, feed_entry: feedparser.FeedParserDict, feed_url, source) -> dict[str, str | datetime.datetime | list]:
        author: str = str(feed_entry.get("author", ""))
        title: str = str(feed_entry.get("title", ""))
        description: str = str(feed_entry.get("description", ""))
        link: str = str(feed_entry.get("link", ""))
        for_hash: str = author + title + link

        published = self.get_published_date(feed_entry)

        content_location = source["parameter_values"].get("CONTENT_LOCATION", None)
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

    def rss_collector(self, feed_url: str, source):
        feed_content = self.make_request(feed_url)
        if not feed_content:
            logger.info(f"RSS-Feed {source['id']} returned no content")
            raise ValueError("RSS returned no content")
        if source["last_attempted"]:
            if last_modified := feed_content.headers.get("Last-Modified"):
                last_modified = dateparser.parse(last_modified, ignoretz=True)
                last_attempted = dateparser.parse(source["last_attempted"], ignoretz=True)
                if last_modified < last_attempted:
                    logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
                    return "Last-Modified < Last-Attempted"
        feed = feedparser.parse(feed_content.content)

        logger.info(f"RSS-Feed {source['id']} returned feed with {len(feed['entries'])} entries")

        news_items = [self.parse_feed(feed_entry, feed_url, source) for feed_entry in feed["entries"][:100]]

        self.publish(news_items, source)
        return None
