import datetime
import hashlib
import json
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

import dateutil.parser as dateparser
import lxml.html
import requests
from bs4 import BeautifulSoup, Tag
from trafilatura import extract, extract_metadata

from worker.collectors.base_collector import BaseCollector, NoChangeError
from worker.collectors.playwright_manager import PlaywrightManager
from worker.log import logger
from worker.types import NewsItem


class BaseWebCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type: str = "BASE_WEB_COLLECTOR"
        self.name: str = "Base Web Collector"
        self.description: str = "Base abstract type for all collectors that use web scraping"

        self.proxies: dict | None = None
        self.timeout: int = 60
        self.last_attempted: datetime.datetime | None = None
        self.headers: dict = {"User-Agent": "TaranisAI/1.0"}
        self.osint_source_id: str

        self.digest_splitting_limit: int
        self.split_digest_urls: list = []

        self.playwright_manager: PlaywrightManager | None = None
        self.browser_mode: str | None = None
        self.web_url: str = ""

    def send_get_request(self, url: str, modified_since: datetime.datetime | None = None) -> requests.Response:
        """Send a GET request to url with self.headers using self.proxies.
        If modified_since is given, make request conditional with If-Modified-Since
        Check for specific status codes and raise rest of errors
        """

        request_headers = self.headers.copy()

        # transform modified_since datetime object to str that is accepted by If-Modified-Since
        if modified_since:
            request_headers["If-Modified-Since"] = modified_since.strftime("%a, %d %b %Y %H:%M:%S GMT")

        logger.debug(f"Sending GET request to {url}")
        response = requests.get(url, headers=request_headers, proxies=self.proxies, timeout=self.timeout)
        if response.status_code == 200 and not response.content:
            logger.info(f"Request to {url} got Response 200 OK, but returned no content")
        if response.status_code == 304:
            raise NoChangeError(f"{url} was not modified")
        if response.status_code == 429:
            raise requests.exceptions.HTTPError("Got Response 429 Too Many Requests. Try decreasing REFRESH_INTERVAL.")
        response.raise_for_status()

        return response

    def parse_source(self, source: dict):
        self.digest_splitting = source["parameters"].get("DIGEST_SPLITTING", "false")
        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))
        self.xpath = source["parameters"].get("XPATH", "")
        self.set_proxies(source["parameters"].get("PROXY_SERVER", None))
        if additional_headers := source["parameters"].get("ADDITIONAL_HEADERS", None):
            self.update_headers(additional_headers)
        if user_agent := source["parameters"].get("USER_AGENT", None):
            self.headers.update({"User-Agent": user_agent})
        self.browser_mode = source["parameters"].get("BROWSER_MODE", "false")

        self.osint_source_id = source["id"]

    def set_proxies(self, proxy_server: str | None):
        self.proxies = {"http": proxy_server, "https": proxy_server, "ftp": proxy_server}

    def update_headers(self, headers: str):
        try:
            headers_dict = json.loads(headers)
            if not isinstance(headers_dict, dict):
                raise ValueError(f"ADDITIONAL_HEADERS: {headers} must be a valid JSON object")
            self.headers.update(headers_dict)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"ADDITIONAL_HEADERS: {headers} has to be valid JSON\n{e}") from e

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

    def update_favicon(self, web_url: str, osint_source_id: str):
        # TODO: Try getting apple-touch-icon first
        icon_url = f"{urlparse(web_url).scheme}://{urlparse(web_url).netloc}/favicon.ico"
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies)
        if not r.ok:
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(osint_source_id, icon_content)
        return None

    def fetch_article_content(self, web_url: str, xpath: str = "") -> tuple[str, datetime.datetime] | tuple[Literal[""], None]:
        if self.browser_mode == "true" and self.playwright_manager:
            return self.playwright_manager.fetch_content_with_js(web_url, xpath), None

        response = self.send_get_request(web_url, self.last_attempted)

        if not response.text:
            return "", None

        if published_date := self.get_last_modified(response):
            return response.text, published_date

        return "", None

    def xpath_extraction(self, html_content: str, xpath: str, get_content: bool = True) -> str | None:
        logger.info(f"Attempting extraction for xpath: {xpath}")
        document = lxml.html.fromstring(html_content)
        if not document.xpath(xpath):
            logger.error(f"No content found for XPath: {xpath}")
            return None
        first_element = document.xpath(xpath)[0]
        if get_content:
            return first_element.text_content()

        return lxml.html.tostring(first_element).decode()  # type: ignore   TODO: set encoding='unicode'

    def clean_url(self, url: str) -> str:
        return url.split("?")[0].split("#")[0]

    def extract_meta(self, web_content: str, web_url: str) -> tuple[str, str]:
        metadata = extract_metadata(web_content, default_url=web_url)
        if metadata is None:
            return "", ""

        author = metadata.as_dict().get("author")
        title = metadata.as_dict().get("title")

        return author or "", title or ""

    def news_item_from_article(self, web_url: str, xpath: str = "") -> NewsItem:
        web_content = self.extract_web_content(web_url, xpath)
        for_hash: str = web_content["author"] + web_content["title"] + self.clean_url(web_url)
        return NewsItem(
            osint_source_id=self.osint_source_id,
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=web_content["author"],
            title=web_content["title"],
            content=web_content["content"],
            web_url=web_url,
            source=self.web_url or web_url,
            published_date=web_content["published_date"],
            language=web_content["language"],
            review=web_content["review"],
        )

    def extract_web_content(self, web_url: str, xpath: str = "") -> dict[str, Any]:
        web_content, published_date = self.fetch_article_content(web_url)
        content = ""
        if xpath and web_content:
            content = self.xpath_extraction(web_content, xpath)
        elif web_content:
            content = extract(web_content, url=web_url)

        if not content or not web_content:
            return {"author": "", "title": "", "content": "", "published_date": None, "language": "", "review": ""}

        author, title = self.extract_meta(web_content, web_url)
        return {"author": author, "title": title, "content": content, "published_date": published_date, "language": "", "review": ""}

    def get_urls(self, collector_url: str, html_content: str) -> list:
        soup = BeautifulSoup(html_content, "html.parser")
        urls = [a["href"] for a in soup.find_all("a", href=True) if isinstance(a, Tag) and a.has_attr("href")]
        return [urljoin(collector_url, url) for url in urls if isinstance(url, str)]

    def parse_digests(self) -> list[NewsItem]:
        news_items = []
        max_elements = min(len(self.split_digest_urls), self.digest_splitting_limit)
        for split_digest_url in self.split_digest_urls[:max_elements]:
            try:
                news_items.append(self.news_item_from_article(split_digest_url))
            except ValueError as e:
                logger.warning(f"Failed to parse the digest with error: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Failed digest splitting with error: {str(e)}")
                raise e

        return news_items
