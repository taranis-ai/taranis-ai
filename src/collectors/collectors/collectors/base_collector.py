import datetime
import hashlib
import uuid
import re

from collectors.managers.log_manager import logger
from collectors.remote.core_api import CoreApi
from shared.schema import collector, osint_source, news_item
from bs4 import BeautifulSoup
from urllib.parse import quote


class BaseCollector:
    type = "BASE_COLLECTOR"
    name = "Base Collector"
    description = "Base abstract type for all collectors"

    def __init__(self):
        self.osint_sources = []
        self.core_api = CoreApi()
        self.refresh()

    def get_info(self):
        info_schema = collector.CollectorSchema()
        return info_schema.dump(self)

    def collect(self, source):
        pass

    @staticmethod
    def history(interval):
        if interval[0].isdigit() and ":" in interval:
            return datetime.datetime.now() - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            return datetime.datetime.now() - datetime.timedelta(weeks=1)
        elif int(interval) > 60:
            hours = int(interval) // 60
            minutes = int(interval) - hours * 60
            return datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)

        else:
            return datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))

    def filter_by_word_list(self, news_items, source):
        if not source.word_lists:
            return news_items
        one_word_list = set()
        for word_list in source.word_lists:
            if word_list.use_for_stop_words is False:
                for category in word_list.categories:
                    for entry in category.entries:
                        one_word_list.add(entry.value.lower())
        if not one_word_list:
            return news_items
        filtered_news_items = []
        for item in news_items:
            for word in one_word_list:
                if word in item.title.lower() or word in item.review.lower() or word in item.content.lower():
                    filtered_news_items.append(item)
                    break
        return filtered_news_items

    def presanitize_html(self, html):
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    def presanitize_url(self, url):
        return quote(url, safe="/:?&")

    def sanitize_news_items(self, news_items, source):
        for item in news_items:
            item.id = item.id or uuid.uuid4()
            item.published = item.published or datetime.datetime.now()
            item.collected = item.collected or datetime.datetime.now()
            item.osint_source_id = item.osint_source_id or source.id
            item.attributes = item.attributes or []
            item.title = self.presanitize_html(item.title)
            item.review = self.presanitize_html(item.review)
            item.content = self.presanitize_html(item.content)
            item.author = self.presanitize_html(item.author)
            item.source = self.presanitize_url(item.source)
            item.link = self.presanitize_url(item.link)
            if item.hash is None:
                for_hash = item.author + item.title + item.link
                item.hash = hashlib.sha256(for_hash.encode()).hexdigest()

    def publish(self, news_items, source):
        self.sanitize_news_items(news_items, source)
        filtered_news_items = self.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        self.core_api.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        logger.log_info(f"Core API requested a refresh of osint sources for {self.type}...")
        response = self.core_api.get_osint_sources(self.type)

        if not response:
            logger.log_debug(f"Got the following reply: {response}")
            return

        try:
            source_schema = osint_source.OSINTSourceSchemaBase(many=True)
            self.osint_sources = source_schema.load(response)

            if not self.osint_sources:
                logger.log_info(f"No osint sources found for {self.type}")
                return

            for source in self.osint_sources:
                self.collect(source)

        except Exception:
            logger.log_debug_trace()
