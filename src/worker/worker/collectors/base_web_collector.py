import datetime
import hashlib
import requests
import lxml.html
import dateutil.parser as dateparser
from urllib.parse import urlparse, urljoin
from trafilatura import extract, extract_metadata
from bs4 import BeautifulSoup
from typing import Any
import json

from worker.log import logger
from worker.types import NewsItem
from worker.collectors.base_collector import BaseCollector
from worker.collectors.playwright_manager import PlaywrightManager


class BaseWebCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "BASE_WEB_COLLECTOR"
        self.name = "Base Web Collector"
        self.description = "Base abstract type for all collectors that use web scraping"

        self.proxies = None
        self.headers = {}
        self.osint_source_id: str

        self.digest_splitting_limit: int
        self.split_digest_urls = []

        self.playwright_manager: PlaywrightManager | None = None
        self.browser_mode = None
        self.web_url: str = ""

    def send_get_request(self, url: str, modified_since: str = "") -> requests.Response | None:
        """Send a GET request to url with self.headers using self.proxies.
        Allows response with 200 OK or 304 Not Modified"""

        # if modified_since string is given, add the If-Modified-Since header
        if modified_since:
            request_headers = dict(self.headers, **{"If-Modified-Since": modified_since})
        else:
            request_headers = self.headers

        try:
            logger.info(f"Sending GET request to {url}")
            response = requests.get(url, headers=request_headers, proxies=self.proxies, timeout=60)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for URL {url}: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Connection to {url} timed out.")
            return None

        # 200 OK and 304 Not Modified are both fine
        if response.ok or not response.status_code == 304:
            logger.error("Response other than 200 OK or 304 Not Modified")
            return None
        return response

    def parse_source(self, source):
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

    def set_proxies(self, proxy_server: str):
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

    def fetch_article_content(self, web_url: str, xpath: str = "", modified_since: str = "") -> tuple[str, datetime.datetime | None]:
        if self.browser_mode == "true" and self.playwright_manager:
            return self.playwright_manager.fetch_content_with_js(web_url, xpath), None

        # send GET request to web_url
        response = self.send_get_request(web_url, modified_since)
        if response is None:
            return "", None  # failure case

        published_date = self.get_last_modified(response)
        if text := response.text:
            return text, published_date

        if response.status_code == 304:  # content was not modified
            logger.info(f"Content of {web_url} was not modified since {modified_since}")
        else:
            logger.error(f"No content found for url: {web_url}")

        return "", published_date

    def xpath_extraction(self, html_content, xpath: str, get_content: bool = True) -> str | None:
        document = lxml.html.fromstring(html_content)
        logger.debug(f"Checking result for XPATH {xpath}: {document.xpath(xpath)}")
        if not document.xpath(xpath):
            logger.error(f"No content found for XPath: {xpath}")
            return None
        first_element = document.xpath(xpath)[0]
        if get_content:
            return first_element.text_content()

        return lxml.html.tostring(first_element).decode()  # type: ignore   TODO: set encoding='unicode'

    def clean_url(self, url: str) -> str:
        return url.split("?")[0].split("#")[0]

    def extract_meta(self, web_content, web_url) -> tuple[str, str]:
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

    def extract_web_content(self, web_url, xpath: str = "", modified_since: str = "") -> dict[str, Any]:
        web_content, published_date = self.fetch_article_content(web_url, modified_since)
        content = ""
        if xpath:
            content = self.xpath_extraction(web_content, xpath)
        elif web_content:
            content = extract(web_content, url=web_url)

        if not content or not web_content:
            return {"author": "", "title": "", "content": "", "published_date": None, "language": "", "review": ""}

        author, title = self.extract_meta(web_content, web_url)
        return {"author": author, "title": title, "content": content, "published_date": published_date, "language": "", "review": ""}

    def get_urls(self, collector_url: str, html_content: str) -> list:
        soup = BeautifulSoup(html_content, "html.parser")
        urls = [a["href"] for a in soup.find_all("a", href=True)]
        return [urljoin(collector_url, url) for url in urls]

    def parse_digests(self) -> list[NewsItem]:
        news_items = []
        max_elements = min(len(self.split_digest_urls), self.digest_splitting_limit)
        for split_digest_url in self.split_digest_urls[:max_elements]:
            try:
                news_items.append(self.news_item_from_article(split_digest_url))
            except ValueError as e:
                logger.warning(f"{self.type}: {self.osint_source_id} failed to parse the digest with error: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"{self.type} failed digest splitting with error: {str(e)}")
                raise e

        return news_items
