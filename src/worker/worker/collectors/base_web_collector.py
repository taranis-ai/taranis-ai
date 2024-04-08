import contextlib
import datetime
import hashlib
import requests
import lxml.html
import dateutil.parser as dateparser
from urllib.parse import urlparse
from trafilatura import extract, extract_metadata

from worker.log import logger
from worker.collectors.base_collector import BaseCollector
from worker.types import NewsItem


class BaseWebCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "BASE_WEB_COLLECTOR"
        self.name = "Base Web Collector"
        self.description = "Base abstract type for all collectors that use web scraping"

        self.proxies = None
        self.headers = {}

    def set_proxies(self, proxy_server: str):
        self.proxies = {"http": proxy_server, "https": proxy_server, "ftp": proxy_server}

    def get_last_modified(self, response: requests.Response) -> datetime.datetime | None:
        if last_modified := response.headers.get("Last-Modified", None):
            return dateparser.parse(last_modified, ignoretz=True)
        return None

    def get_last_attempted(self, source: dict) -> datetime.datetime | None:
        if last_attempted := source.get("last_attempted"):
            try:
                return dateparser.parse(last_attempted, ignoretz=True)
            except Exception:
                return None
        return None

    def update_favicon(self, web_url: str, source_id: str):
        # TODO: Try getting apple-touch-icon first
        icon_url = f"{urlparse(web_url).scheme}://{urlparse(web_url).netloc}/favicon.ico"
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies)
        if not r.ok:
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(source_id, icon_content)
        return None

    def web_content_from_article(self, web_url: str) -> tuple[str, datetime.datetime | None]:
        response = requests.get(web_url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response or not response.ok:
            return "", None
        published_date = self.get_last_modified(response)
        if text := response.text:
            return text, published_date
        return "", published_date

    def xpath_extraction(self, html_content, xpath: str) -> str | None:
        document = lxml.html.fromstring(html_content)
        if not document.xpath(xpath):
            logger.error(f"No content found for XPath: {xpath}")
            return None
        return document.xpath(xpath)[0].text_content()

    def clean_url(self, url: str) -> str:
        return url.split("?")[0].split("#")[0]

    def extract_meta(self, web_content, web_url) -> tuple[str, str]:
        # See https://github.com/adbar/htmldate/pull/145
        with contextlib.suppress(ValueError):
            metadata = extract_metadata(web_content, default_url=web_url)
        if metadata is None:
            return "", ""

        author = metadata.as_dict().get("author")
        title = metadata.as_dict().get("title")

        return author or "", title or ""

    def news_item_from_article(self, web_url: str, source_id: str, xpath: str = "") -> NewsItem:
        web_content = self.parse_web_content(web_url, xpath)
        return self.create_news_item(
            web_content["author"],
            web_content["title"],
            web_content["content"],
            web_url,
            web_content["published_date"],
            source_id,
        ).to_dict()

    def parse_web_content(self, web_url, xpath: str = "") -> dict[str, str | datetime.datetime | None]:
        web_content, published_date = self.web_content_from_article(web_url)
        content = ""
        if xpath:
            content = self.xpath_extraction(web_content, xpath)
        elif web_content is not None:
            content = extract(web_content, url=web_url)

        if not content or not web_content:
            raise ValueError("No content found")

        author, title = self.extract_meta(web_content, web_url)
        return {"author": author, "title": title, "content": content, "published_date": published_date}

    def create_news_item(
        self, author: str, title: str, content: str, web_url: str, published_date: datetime.datetime | None, source_id: str
    ) -> NewsItem:
        for_hash: str = author + title + self.clean_url(web_url)

        return NewsItem(
            source_id=source_id,
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            content=content,
            web_url=web_url,
            published_date=published_date,
        )
