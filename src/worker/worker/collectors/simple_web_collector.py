import datetime
import hashlib
import uuid
import requests
import logging
from urllib.parse import urlparse
import dateutil.parser as dateparser
from trafilatura import bare_extraction

from .base_collector import BaseCollector
from worker.log import logger


class SimpleWebCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "SIMPLE_WEB_COLLECTOR"
        self.name = "Simple Web Collector"
        self.description = "Collector for gathering news with Trafilatura"

        self.news_items = []
        self.proxies = None
        self.headers = {}
        logger_trafilatura = logging.getLogger("trafilatura")
        logger_trafilatura.setLevel(logging.WARNING)

    def collect(self, source):
        web_url = source["parameters"].get("WEB_URL", None)
        if not web_url:
            logger.warning("No WEB_URL set")
            return "No WEB_URL set"

        logger.info(f"Website {source['id']} Starting collector for url: {web_url}")

        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers = {"User-Agent": user_agent}

        try:
            return self.web_collector(web_url, source)
        except Exception as e:
            logger.exception()
            logger.error(f"RSS collector for {web_url} failed with error: {str(e)}")
            return str(e)

    def set_proxies(self, proxy_server: str):
        self.proxies = {"http": proxy_server, "https": proxy_server, "ftp": proxy_server}

    def get_last_modified(self, response: requests.Response) -> datetime.datetime:
        if last_modified := response.headers.get("Last-Modified", None):
            return dateparser.parse(last_modified, ignoretz=True)
        return datetime.datetime.now()

    def get_article_content(self, web_url: str) -> tuple[str, datetime.datetime]:
        response = requests.get(web_url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response or not response.ok:
            return "", datetime.datetime.now()
        html_content = response.content.decode("utf-8") if response is not None else ""
        published_date = self.get_last_modified(response)
        return html_content, published_date

    def parse_web_content(self, web_url, source_id: str) -> dict[str, str | datetime.datetime | list]:
        html_content, published_date = self.get_article_content(web_url)
        extract_document = bare_extraction(html_content, with_metadata=True, include_comments=False, url=web_url)
        author = extract_document["author"] or ""
        title = extract_document["title"] or ""
        for_hash: str = author + title + web_url
        content = extract_document["text"] or ""

        return {
            "id": str(uuid.uuid4()),
            "hash": hashlib.sha256(for_hash.encode()).hexdigest(),
            "title": title,
            "review": "",
            "source": web_url,
            "link": web_url,
            "published": published_date,
            "author": author,
            "collected": datetime.datetime.now(),
            "content": content,
            "osint_source_id": source_id,
            "attributes": [],
        }

    def get_last_attempted(self, source: dict) -> datetime.datetime | None:
        if last_attempted := source.get("last_attempted"):
            try:
                return dateparser.parse(last_attempted, ignoretz=True)
            except Exception:
                return None
        return None

    def update_favicon(self, web_url: str, source_id: str):
        icon_url = f"{urlparse(web_url).scheme}://{urlparse(web_url).netloc}/favicon.ico"
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies)
        if not r.ok:
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(source_id, icon_content)
        return None

    def web_collector(self, web_url: str, source):
        response = requests.head(web_url, headers=self.headers, proxies=self.proxies)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content")

        last_attempted = self.get_last_attempted(source)
        if not last_attempted:
            self.update_favicon(web_url, source["id"])
        last_modified = self.get_last_modified(response)
        self.last_modified = last_modified
        if last_modified and last_attempted and last_modified < last_attempted:
            logger.debug(f"Last-Modified: {last_modified} < Last-Attempted {last_attempted} skipping")
            return "Last-Modified < Last-Attempted"

        news_items = self.parse_web_content(web_url, source["id"])

        self.publish(news_items, source)
        return None
