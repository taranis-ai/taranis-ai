import datetime
import hashlib
import uuid
import re

from bs4 import BeautifulSoup
from urllib.parse import quote
from worker.log import logger
from worker.core_api import CoreApi
from worker.tasks import execute_bot

class BaseCollector:
    def __init__(self):
        self.type = "BASE_COLLECTOR"
        self.name = "Base Collector"
        self.description = "Base abstract type for all collectors"

        self.core_api = CoreApi()

    def filter_by_word_list(self, news_items, source):
        if not source["word_lists"]:
            return news_items
        one_word_list = set()
        for word_list in source["word_lists"]:
            if not word_list.use_for_stop_words:
                for category in word_list.categories:
                    for entry in category.entries:
                        one_word_list.add(entry.value.lower())
        if not one_word_list:
            return news_items
        filtered_news_items = []
        for item in news_items:
            for word in one_word_list:
                if word in item["title"].lower() or word in item["review"].lower() or word in item["content"].lower():
                    filtered_news_items.append(item)
                    break
        return filtered_news_items


    def collect(self, source: dict):
        pass

    def sanitize_html(self, html: str):
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    def sanitize_url(self, url: str):
        return quote(url, safe="/:?&")

    def sanitize_date(self, date: str):
        if isinstance(date, datetime.datetime):
            return date.isoformat()
        return datetime.datetime.now().isoformat()

    def sanitize_news_item(self, item, source):
        item["id"] = item["id"] or str(uuid.uuid4())
        item["published"] = self.sanitize_date(item["published"])
        item["collected"] = self.sanitize_date(item["collected"])
        item["osint_source_id"] = item["osint_source_id"] or source["id"]
        item["attributes"] = item["attributes"] or []
        item["title"] = self.sanitize_html(item["title"])
        item["review"] = self.sanitize_html(item["review"])
        item["content"] = self.sanitize_html(item["content"])
        item["author"] = self.sanitize_html(item["author"])
        item["source"] = self.sanitize_url(item["source"])
        item["link"] = self.sanitize_url(item["link"])
        item["hash"] = item["hash"] or hashlib.sha256(item["author"] + item["title"] + item["link"]).hexdigest()

    def publish(self, news_items, source):
        logger.info(f"Publishing {len(news_items)} news items to core api")
        for item in news_items:
            item = self.sanitize_news_item(item, source)
        if "word_lists" in source:
            news_items = self.filter_by_word_list(news_items, source)
        self.core_api.add_news_items(news_items)
        execute_bot.delay("NLP_BOT", {"SOURCE": source["id"]})
