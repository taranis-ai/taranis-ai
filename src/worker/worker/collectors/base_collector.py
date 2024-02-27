import datetime
import hashlib
import uuid
import re
from bs4 import BeautifulSoup
from urllib.parse import quote

from worker.log import logger
from worker.core_api import CoreApi


class BaseCollector:
    def __init__(self):
        self.type = "BASE_COLLECTOR"
        self.name = "Base Collector"
        self.description = "Base abstract type for all collectors"

        self.core_api = CoreApi()

    def filter_by_word_list(self, news_items, source):
        if not source["word_lists"]:
            return news_items
        include_list = set()
        exclude_list = set()

        for word_list in source["word_lists"]:
            if "COLLECTOR_INCLUDELIST" in word_list["usage"]:
                for entry in word_list["entries"]:
                    include_list.add(entry["value"])

            if "COLLECTOR_EXCLUDELIST" in word_list["usage"]:
                for entry in word_list["entries"]:
                    exclude_list.add(entry["value"])

        items = (
            [
                item
                for item in news_items
                if any(
                    re.search(r"\b" + re.escape(word) + r"\b", "".join(item["title"] + item["review"] + item["content"]), re.IGNORECASE)
                    for word in include_list
                )
            ]
            if include_list
            else news_items
        )

        if exclude_list:
            items = [
                item
                for item in items
                if not any(
                    re.search(r"\b" + re.escape(word) + r"\b", "".join(item["title"] + item["review"] + item["content"]), re.IGNORECASE)
                    for word in exclude_list
                )
            ]

        return items

    # Use filtered_items for further processing

    def collect(self, source: dict):
        pass

    def sanitize_html(self, html: str):
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    def sanitize_url(self, url: str):
        return quote(url, safe="/:?&=")

    def sanitize_date(self, date: str | None):
        if isinstance(date, datetime.datetime):
            return date.isoformat()
        return datetime.datetime.now().isoformat()

    def sanitize_news_item(self, item: dict, source: dict):
        item["id"] = item.get("id", str(uuid.uuid4()))
        item["published"] = self.sanitize_date(item.get("published"))
        item["collected"] = self.sanitize_date(item.get("collected"))
        item["osint_source_id"] = item.get("osint_source_id", source.get("id"))
        item["attributes"] = item.get("attributes", [])
        item["title"] = self.sanitize_html(item.get("title", ""))
        item["review"] = self.sanitize_html(item.get("review", ""))
        item["content"] = self.sanitize_html(item.get("content", ""))
        item["author"] = self.sanitize_html(item.get("author", ""))
        item["source"] = self.sanitize_url(item.get("source", ""))
        item["link"] = self.sanitize_url(item.get("link", ""))
        item["hash"] = item.get("hash", hashlib.sha256((item["author"] + item["title"] + item["link"]).encode()).hexdigest())

    def publish(self, news_items: list[dict], source: dict):
        if "word_lists" in source:
            news_items = self.filter_by_word_list(news_items, source)
        for item in news_items:
            item = self.sanitize_news_item(item, source)
        logger.info(f"Publishing {len(news_items)} news items to core api")
        for item in news_items:
            item = self.sanitize_news_item(item, source)
        if "word_lists" in source:
            news_items = self.filter_by_word_list(news_items, source)
        self.core_api.add_news_items(news_items)
        self.core_api.update_osintsource_status(source["id"], None)
