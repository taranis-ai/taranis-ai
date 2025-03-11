import contextlib
import datetime
import hashlib
import uuid
import re
from bs4 import BeautifulSoup
from urllib.parse import quote

from worker.log import logger
from worker.core_api import CoreApi
from worker.types import NewsItem


class BaseCollector:
    def __init__(self):
        self.type = "BASE_COLLECTOR"
        self.name = "Base Collector"
        self.description = "Base abstract type for all collectors"

        self.core_api = CoreApi()

    def filter_by_word_list(self, news_items: list[NewsItem], word_lists: list) -> list[NewsItem]:
        if not word_lists:
            return news_items

        include_patterns: set[re.Pattern] = {
            re.compile(r"\b" + re.escape(entry["value"]) + r"\b", re.IGNORECASE)
            for word_list in word_lists
            if "COLLECTOR_INCLUDELIST" in word_list["usage"]
            for entry in word_list["entries"]
        }

        exclude_patterns: set[re.Pattern] = {
            re.compile(r"\b" + re.escape(entry["value"]) + r"\b", re.IGNORECASE)
            for word_list in word_lists
            if "COLLECTOR_EXCLUDELIST" in word_list["usage"]
            for entry in word_list["entries"]
        }
        if include_patterns or exclude_patterns:
            return [
                item
                for item in news_items
                if (not include_patterns or any(pattern.search(item.title + item.content) for pattern in include_patterns))
                and (not exclude_patterns or all(not pattern.search(item.title + item.content) for pattern in exclude_patterns))
            ]

        return news_items

    def add_tlp(self, news_items: list[NewsItem], tlp_level: str) -> list[NewsItem]:
        for item in news_items:
            item.attributes.append({"key": "TLP", "value": tlp_level})
        return news_items

    def collect(self, source: dict, manual: bool = False):
        raise NotImplementedError

    def preview_collector(self, source: dict) -> list[dict]:
        raise NotImplementedError

    def sanitize_html(self, html: str):
        if not html:
            return ""
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    def sanitize_url(self, url: str):
        """
        Sanitize URL to be compliant with RFC 3986
        """
        return quote(url, safe="/:@?&=+$,;")

    def sanitize_date(self, date: str | None | datetime.datetime) -> datetime.datetime:
        if isinstance(date, datetime.datetime):
            return date
        if isinstance(date, str):
            with contextlib.suppress(ValueError):
                return datetime.datetime.fromisoformat(date)
        return datetime.datetime.now()

    def sanitize_news_item(self, item: NewsItem, source: dict) -> NewsItem:
        if not item.osint_source_id:
            item.osint_source_id = str(uuid.uuid4())
        item.published_date = self.sanitize_date(item.published_date)
        item.collected_date = self.sanitize_date(item.collected_date)
        item.osint_source_id = source.get("id", item.osint_source_id)
        item.attributes = item.attributes or []
        item.title = self.sanitize_html(item.title)
        item.content = self.sanitize_html(item.content)
        item.review = item.review or ""
        item.author = item.author or ""
        item.web_url = self.sanitize_url(item.web_url)
        item.hash = item.hash or hashlib.sha256((item.author + item.title + item.web_url).encode()).hexdigest()
        return item

    def preview(self, news_items: list[NewsItem], source: dict) -> list[dict]:
        news_items = self.process_news_items(news_items, source)
        logger.info(f"Previewing {len(news_items)} news items")
        return [n.to_dict() for n in news_items]

    def process_news_items(self, news_items: list[NewsItem], source: dict) -> list[NewsItem]:
        if word_lists := source.get("word_lists"):
            news_items = self.filter_by_word_list(news_items, word_lists)
        if tlp_level := source["parameters"].get("TLP_LEVEL", None):
            news_items = self.add_tlp(news_items, tlp_level)

        news_items = [self.sanitize_news_item(item, source) for item in news_items if item.title or item.content]

        return news_items

    def publish(self, news_items: list[NewsItem], source: dict):
        news_items = self.process_news_items(news_items, source)
        logger.info(f"Publishing {len(news_items)} news items to core api")
        news_items_dicts = [item.to_dict() for item in news_items]
        self.core_api.add_news_items(news_items_dicts)
        self.core_api.update_osintsource_status(source["id"], None)

    def publish_or_update_stories(self, story_lists: list[dict], source: dict, story_attribute_key: str | None = None):
        """story_lists example: [{title: str, news_items: list[NewsItem]}]"""

        if not story_attribute_key:
            news_items = [item for story_list in story_lists for item in story_list["news_items"]]
            return self.publish(news_items, source)

        stories_for_publishing = self.find_existing_stories(story_lists, story_attribute_key, source)
        for story in stories_for_publishing:
            if "news_items" in story:
                story["news_items"] = [item.to_dict() for item in story["news_items"]]
            self.core_api.add_or_update_story(story)

    def find_existing_stories(self, new_stories: list[dict], story_attribute_key: str, source: dict) -> list[dict]:
        # Get existing stories from core api. For each new story,
        # if any dict in the "attributes" list of an existing story has a matching key-value pair,
        # assign the existing story's id to the new story.

        existing_stories = self.core_api.get_stories({"source": source["id"]})
        if not existing_stories:
            return new_stories

        for story in new_stories:
            new_story_value = story.get(story_attribute_key)
            for existing_story in existing_stories:
                attributes = existing_story.get("attributes", [])
                for attribute in attributes:
                    if attribute.get(story_attribute_key) == new_story_value:
                        story["id"] = existing_story["id"]
                        break
                if "id" in story:
                    break

        return new_stories
