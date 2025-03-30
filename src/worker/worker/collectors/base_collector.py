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
        if not item.id:
            item.id = str(uuid.uuid4())
        if not item.osint_source_id:
            if source.get("id"):
                item.osint_source_id = source.get("id", "")
            else:
                raise ValueError("osint_source_id is required")
        item.published_date = self.sanitize_date(item.published_date)
        item.collected_date = self.sanitize_date(item.collected_date)
        item.attributes = item.attributes or []
        item.title = self.sanitize_html(item.title)
        item.content = self.sanitize_html(item.content)
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
        """
        story_lists example: [{title: str, news_items: list[NewsItem]}]
        """
        if not story_lists:
            logger.info(f"No stories to publish from source {source.get('name')} ({source.get('id')})")
            return None

        if not story_attribute_key:
            news_items = [item for story_list in story_lists for item in story_list["news_items"]]
            return self.publish(news_items, source)

        stories_for_publishing = self.find_existing_stories(story_lists, story_attribute_key, source)

        processed_stories = []
        for story in stories_for_publishing:
            new_story = story.copy()
            if news_items := new_story.get("news_items"):
                processed_news_items = self.process_news_items(news_items, source)
                new_story["news_items"] = [item.to_dict() for item in processed_news_items]
                logger.debug(f"{new_story['news_items']=}")
            processed_stories.append(new_story)

        if processed_stories[0].get("id"):
            self.publish_misp_stories(processed_stories, story_attribute_key, source)

        for story in processed_stories:
            self.core_api.add_or_update_story(story)

    def find_existing_stories(self, new_stories: list[dict], story_attribute_key: str, source: dict) -> list[dict]:
        existing_stories = self.core_api.get_stories({"source": source["id"]})
        if not existing_stories:
            return new_stories

        for story in new_stories:
            story_attributes = story.get("attributes", [])
            # Find the attribute dict where key = story_attribute_key and get its value
            story_attr_value = None
            for attr in story_attributes:
                if attr.get("key") == story_attribute_key:
                    story_attr_value = attr.get("value")
                    break

            if story_attr_value is None:
                continue

            for existing_story in existing_stories:
                existing_attributes = existing_story.get("attributes", [])
                for existing_attr in existing_attributes:
                    if existing_attr.get("key") == story_attribute_key and story_attr_value == existing_attr.get("value"):
                        story["id"] = existing_story.get("id")
                        break
                if "id" in story:
                    break

        return new_stories

    def publish_misp_stories(self, story_lists: list[dict], story_attribute_key: str, source: dict):
        for story in story_lists:
            if existing_story := self.core_api.get_stories({"story_id": story.get("id")}):
                if len(existing_story) > 1:
                    logger.warning(f"Multiple stories with the same story_id {story.get('id')} found")
                    continue
                if self.check_internal_changes(existing_story[0]):
                    logger.info(f"Internal changes detected in story {existing_story[0].get('id')}, skipping update")
                    story["conflict"] = True

                if news_items_to_delete := self.get_news_items_to_delete(story, existing_story[0]):
                    story["news_items_to_delete"] = news_items_to_delete

                self.core_api.add_or_update_story(story)

    def check_internal_changes(self, existing_story) -> bool:
        if existing_story.get("last_change") == "internal":
            return True
        return any(news_item.get("last_change") == "internal" for news_item in existing_story.get("news_items"))

    def get_news_items_to_delete(self, new_story: dict, existing_story: dict) -> list:
        existing_news_items = existing_story.get("news_items", [])
        new_news_items = new_story.get("news_items", [])

        existing_ids = {item.get("id") for item in existing_news_items if item.get("id") is not None}
        new_ids = {item.get("id") for item in new_news_items if item.get("id") is not None}

        return list(existing_ids - new_ids)
