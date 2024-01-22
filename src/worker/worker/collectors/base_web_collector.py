import datetime
import requests
import lxml.html
import dateutil.parser as dateparser
from urllib.parse import urlparse

from worker.log import logger
from worker.collectors.base_collector import BaseCollector


class BaseWebCollector(BaseCollector):
    def __init__(self):
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

    def html_from_article(self, web_url: str) -> tuple[str, datetime.datetime]:
        response = requests.get(web_url, headers=self.headers, proxies=self.proxies, timeout=60)
        if not response or not response.ok:
            return "", datetime.datetime.now()
        html_content = response.content.decode("utf-8")
        published_date = self.get_last_modified(response)
        return html_content, published_date

    def xpath_extraction(self, html_content, xpath: str) -> str:
        document = lxml.html.fromstring(html_content)
        if not document.xpath(xpath):
            logger.error(f"No content found for XPath: {xpath}")
            return ""
        return document.xpath(xpath)[0].text_content()
