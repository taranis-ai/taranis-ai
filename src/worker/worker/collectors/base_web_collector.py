import contextlib
import datetime
import hashlib
import requests
import lxml.html
import dateutil.parser as dateparser
from urllib.parse import urlparse, urljoin
from trafilatura import extract, extract_metadata
from bs4 import BeautifulSoup
import json

from worker.log import logger
from worker.types import NewsItem
from worker.collectors.base_collector import BaseCollector


class BaseWebCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "BASE_WEB_COLLECTOR"
        self.name = "Base Web Collector"
        self.description = "Base abstract type for all collectors that use web scraping"

        self.proxies = None
        self.headers = {}
        self.osint_source_id = None

        self.digest_splitting_limit = None
        self.split_digest_urls = []

        self.playwright_manager = None
        self.browser_mode = None

    def parse_source(self, source):
        self.digest_splitting = source["parameters"].get("DIGEST_SPLITTING", "false")
        self.digest_splitting_limit = int(source["parameters"].get("DIGEST_SPLITTING_LIMIT", 30))
        self.xpath = source["parameters"].get("XPATH", "")
        self.set_proxies(source["parameters"].get("PROXY_SERVER", None))
        if additional_headers := source["parameters"].get("ADDITIONAL_HEADERS", None):
            self.update_headers(additional_headers)
        if user_agent := source["parameters"].get("USER_AGENT", None):
            user_agent_dict = {"User-Agent": user_agent}
            self.update_headers(json.dumps(user_agent_dict))
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

    def fetch_article_content(self, web_url: str, xpath: str = "") -> tuple[str, datetime.datetime | None]:
        if self.browser_mode == "true":
            return self.playwright_manager.fetch_content_with_js(web_url, xpath), None
        response = requests.get(web_url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response or not response.ok:
            return "", None
        published_date = self.get_last_modified(response)
        if text := response.text:
            return text, published_date
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

        return lxml.html.tostring(first_element).decode()

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

    def news_item_from_article(self, web_url: str, xpath: str = "") -> NewsItem:
        web_content = self.extract_web_content(web_url, xpath)
        return self.create_news_item(
            web_content["author"],
            web_content["title"],
            web_content["content"],
            web_url,
            web_content["published_date"],
            self.osint_source_id,
            web_content["language"],
            web_content["review"],
        )

    def extract_web_content(self, web_url, xpath: str = "") -> dict[str, str | datetime.datetime | None]:
        web_content, published_date = self.fetch_article_content(web_url)
        content = ""
        if xpath:
            content = self.xpath_extraction(web_content, xpath)
        elif web_content:
            content = extract(web_content, url=web_url)

        if not content or not web_content:
            logger.error(f"No content found for url: {web_url}")
            return {"author": "", "title": "", "content": "", "published_date": None, "language": "", "review": ""}

        author, title = self.extract_meta(web_content, web_url)
        return {"author": author, "title": title, "content": content, "published_date": published_date, "language": "", "review": ""}

    def create_news_item(
        self,
        author: str,
        title: str,
        content: str,
        web_url: str,
        published_date: datetime.datetime | None,
        osint_source_id: str,
        language: str = None,
        review: str = None,
    ) -> NewsItem:
        for_hash: str = author + title + self.clean_url(web_url)

        return NewsItem(
            osint_source_id=osint_source_id,
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            content=content,
            web_url=web_url,
            published_date=published_date,
            language=language,
            review=review,
        )

    def get_urls(self, collector_url: str, html_content: str) -> list:
        soup = BeautifulSoup(html_content, "html.parser")
        urls = [a["href"] for a in soup.find_all("a", href=True)]
        return [urljoin(collector_url, url) for url in urls]

    def parse_digests(self) -> list[NewsItem] | str:
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
