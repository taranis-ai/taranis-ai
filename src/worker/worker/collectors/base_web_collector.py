import datetime
import hashlib
import uuid
import requests
import lxml.html
import dateutil.parser as dateparser
from urllib.parse import urlparse
from trafilatura import bare_extraction, extract_metadata

from worker.log import logger
from worker.collectors.base_collector import BaseCollector


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

    def get_last_modified(self, response: requests.Response) -> datetime.datetime:
        if last_modified := response.headers.get("Last-Modified", None):
            return dateparser.parse(last_modified, ignoretz=True)
        return datetime.datetime.now()

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

    def web_content_from_article(self, web_url: str) -> tuple[str, datetime.datetime]:
        response = requests.get(web_url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response or not response.ok:
            return "", datetime.datetime.now()
        # Handle non-text content
        if response.headers["Content-Type"].startswith("text/"):
            html_content = response.content.decode("utf-8")
        else:
            html_content = response.content
        published_date = self.get_last_modified(response)
        return html_content, published_date

    def xpath_extraction(self, html_content, xpath: str) -> str:
        document = lxml.html.fromstring(html_content)
        if not document.xpath(xpath):
            logger.error(f"No content found for XPath: {xpath}")
            return ""
        return document.xpath(xpath)[0].text_content()

    def extract_meta(self, web_content, web_url):
        # Trafilatura.extract_metadata() raises for certain URLs a ValueError
        # Example URL: https://www.mozilla.org/en-US/security/advisories/mfsa2024-17/
        # Example error message: "month must be in 1..12"
        metadata = extract_metadata(web_content, default_url=web_url)
        author = "" if metadata is None or metadata.as_dict().get("author") is None else metadata.as_dict().get("author")
        title = "Title not collected" if metadata is None or metadata.as_dict().get("title") is None else metadata.as_dict().get("title")

        return author, title

    def extract_content(self, web_content, web_url):
        extract_document = bare_extraction(web_content, url=web_url, with_metadata=False, include_comments=False)
        if extract_document is None:
            return {"error": "No content found"}
        text = extract_document.get("text")
        content = {"value": text}
        return {"error": "No content found"} if text is None else content

    def parse_web_content(self, web_url, source_id: str, xpath: str = "") -> dict[str, str | datetime.datetime | list]:
        web_content, published_date = self.web_content_from_article(web_url)
        content = ""
        if xpath:
            content = self.xpath_extraction(web_content, xpath)
        elif web_content is not None:
            content = self.extract_content(web_content, web_url)
            if content.get("error"):
                logger.warning(f"Failed to extract content from {web_url}")
                return content

        author, title = self.extract_meta(web_content, web_url)

        for_hash: str = author + title + web_url

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
            "content": content.get("value"),
            "osint_source_id": source_id,
            "attributes": [],
        }
