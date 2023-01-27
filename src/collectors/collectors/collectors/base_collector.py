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
    def print_exception(source, error):
        logger.log_info(f"OSINTSource ID: {source.id}")
        logger.log_info(f"OSINTSource name: {source.name}")
        if str(error).startswith("b"):
            logger.log_info(f"ERROR: {str(error)[2:-1]}")
        else:
            logger.log_info(f"ERROR: {str(error)}")

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

    @staticmethod
    def filter_by_word_list(news_items, source):
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

    @staticmethod
    def presanitize_html(html):
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    @staticmethod
    def presanitize_url(url):
        return quote(url, safe="/:?&")

    @staticmethod
    def sanitize_news_items(news_items, source):
        for item in news_items:
            item.id = item.id or uuid.uuid4()
            item.title = item.title or ""
            item.review = item.review or ""
            item.source = item.source or ""
            item.link = item.link or ""
            item.author = item.author or ""
            item.content = item.content or ""
            item.published = item.published or datetime.datetime.now()
            item.collected = item.collected or datetime.datetime.now()
            item.osint_source_id = item.osint_source_id or source.id
            item.attributes = item.attributes or []
            item.title = BaseCollector.presanitize_html(item.title)
            item.review = BaseCollector.presanitize_html(item.review)
            item.content = BaseCollector.presanitize_html(item.content)
            item.author = BaseCollector.presanitize_html(item.author)
            item.source = BaseCollector.presanitize_url(item.source)
            item.link = BaseCollector.presanitize_url(item.link)
            if item.hash is None:
                for_hash = item.author + item.title + item.link
                item.hash = hashlib.sha256(for_hash.encode()).hexdigest()

    def publish(self, news_items, source):
        BaseCollector.sanitize_news_items(news_items, source)
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        self.core_api.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        logger.log_info(f"Core API requested a refresh of osint sources for {self.type}...")
        response, code = self.core_api.get_osint_sources(self.type)

        if code != 200 or response is None:
            logger.log_debug(f"HTTP {code}: Got the following reply: {response}")
            return

        try:
            source_schema = osint_source.OSINTSourceSchemaBase(many=True)
            self.osint_sources = source_schema.load(response)

            for source in self.osint_sources:
                self.collect(source)

        except Exception:
            logger.log_debug_trace()
