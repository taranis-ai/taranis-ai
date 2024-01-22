import datetime
import hashlib
import uuid
import requests
import logging
import lxml.html
from trafilatura import bare_extraction

from worker.log import logger
from .base_web_collector import BaseWebCollector


class SimpleWebCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "SIMPLE_WEB_COLLECTOR"
        self.name = "Simple Web Collector"
        self.description = "Collector for gathering news with Trafilatura"

        self.news_items = []
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

        xpath = source["parameters"].get("XPATH", "")
        try:
            return self.web_collector(web_url, source, xpath)
        except Exception as e:
            logger.exception()
            logger.error(f"Simple Web Collector for {web_url} failed with error: {str(e)}")
            return str(e)

    def parse_web_content(self, web_url, source_id: str, xpath: str = "") -> dict[str, str | datetime.datetime | list]:
        html_content, published_date = self.html_from_article(web_url)
        author, title = self.extract_meta(html_content)

        if xpath:
            content = self.xpath_extraction(html_content, xpath)
        else:
            extract_document = bare_extraction(html_content, with_metadata=True, include_comments=False, url=web_url)
            author = extract_document["author"] or ""
            title = extract_document["title"] or ""
            content = extract_document["text"] or ""

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
            "content": content,
            "osint_source_id": source_id,
            "attributes": [],
        }

    def extract_meta(self, html_content):
        html_content = lxml.html.fromstring(html_content)
        author = ""
        title = html_content.findtext(".//title", default="")

        if meta_tags := html_content.xpath("//meta[@name='author']"):
            author = meta_tags[0].get("content", "")

        return author, title

    def web_collector(self, web_url: str, source, xpath: str = ""):
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

        news_item = self.parse_web_content(web_url, source["id"], xpath)

        self.publish([news_item], source)
        return None
