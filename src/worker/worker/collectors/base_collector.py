import asyncio
import base64
import json
import re
from typing import Any

from models.assess import NewsItem
from niquests.exceptions import RequestException

from worker.collectors.news_images import download_image
from worker.core_api import CoreApi
from worker.log import logger


class NoChangeError(Exception):
    """Custom exception for when a source didn't change."""

    def __init__(self, message: str = "Not modified"):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class BaseCollector:
    def __init__(self):
        self.type = "BASE_COLLECTOR"
        self.name = "Base Collector"
        self.description = "Base abstract type for all collectors"

        self.core_api = CoreApi()
        self.skipped_images = 0
        self.affected_story_ids: set[str] = set()

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

            def matches_filters(item: NewsItem) -> bool:
                searchable_text = f"{item.title or ''} {item.content or ''}"
                return (not include_patterns or any(pattern.search(searchable_text) for pattern in include_patterns)) and (
                    not exclude_patterns or all(not pattern.search(searchable_text) for pattern in exclude_patterns)
                )

            return [item for item in news_items if matches_filters(item)]

        return news_items

    def add_tlp(self, news_items: list[NewsItem], tlp_level: str) -> list[NewsItem]:
        for item in news_items:
            if item.attributes is None:
                item.attributes = [{"key": "TLP", "value": tlp_level}]
            else:
                item.attributes.append({"key": "TLP", "value": tlp_level})
        return news_items

    def collect(self, source: dict, manual: bool = False) -> Any:
        raise NotImplementedError

    def preview_collector(self, source: dict) -> list[dict]:
        raise NotImplementedError

    def preview(self, news_items: list[NewsItem], source: dict) -> list[dict]:
        news_items = self.process_news_items(news_items, source)
        logger.info(f"Previewing {len(news_items)} news items")
        return [n.model_dump(mode="json") for n in news_items]

    def process_news_items(self, news_items: list[NewsItem], source: dict) -> list[NewsItem]:
        if word_lists := source.get("word_lists"):
            news_items = self.filter_by_word_list(news_items, word_lists)

        return news_items

    def process_news_items_in_stories(self, stories: list[dict], source: dict, story_attribute_key: str | None = None) -> list[dict]:
        processed_stories = []
        for story in stories:
            new_story = story.copy()
            if news_items := new_story.get("news_items"):
                processed_news_items = self.process_news_items(news_items, source)
                new_story["news_items"] = [item.model_dump(mode="json") for item in processed_news_items]
            processed_stories.append(new_story)
        return processed_stories

    async def _capture_images(self, candidates: dict[str, str | None], proxy_server: str | None, remaining: int) -> list[dict]:
        slots = asyncio.Semaphore(3)

        async def capture(url: str, alt_text: str | None) -> dict | None:
            async with slots:
                try:
                    blob = await download_image(url, proxy_server=proxy_server)
                    return {"source_url": url, "alt_text": alt_text, "data": base64.b64encode(blob).decode("ascii")}
                except (OSError, ValueError, RequestException):
                    return None

        captures = []
        for image in await asyncio.gather(*(capture(url, alt) for url, alt in candidates.items())):
            if image is not None:
                size = len(image["data"]) + len(json.dumps(image["source_url"])) + len(json.dumps(image["alt_text"])) + 64
                if size <= remaining:
                    remaining -= size
                    captures.append(image)
                    continue
            self.skipped_images += 1
        return captures

    def publish_with_images(self, items: list[NewsItem], source: dict) -> dict:
        try:
            for item in self.process_news_items(items, source):
                payload = item.model_dump(mode="json")
                candidates = item.image_candidates
                if candidates:
                    identity = {"osint_source_id": item.osint_source_id, "link": item.link, "title": item.title}
                    if not item.link or not item.title:
                        identity["content"] = item.content
                    known = self.core_api.get_known_news_item_images(identity)
                    payload["known_image_descriptions"] = {known[url]: alt for url, alt in candidates.items() if url in known and alt}
                    candidates = {url: alt for url, alt in candidates.items() if url not in known}
                # Leave room for the JSON envelope within Core's 50 MiB request limit.
                remaining = 49 * 1024 * 1024 - len(json.dumps(payload).encode())
                payload["captured_images"] = asyncio.run(
                    self._capture_images(candidates, source["parameters"].get("PROXY_SERVER"), remaining)
                )
                result = self.core_api.add_news_items([payload])
                if result:
                    self.affected_story_ids.update(result.get("story_ids", []))
                if not result or result.get("error"):
                    raise RuntimeError("Cannot add news items")
                self.skipped_images += result.get("skipped_images", 0)
        except Exception:
            if self.affected_story_ids:
                self.core_api.run_post_collection_bots(source["id"], sorted(self.affected_story_ids))
            logger.exception("Could not publish collected article with images")
            raise RuntimeError("Cannot add news items") from None
        message = f"Collected {len(self.affected_story_ids)} stories" if self.affected_story_ids else "All news items were skipped"
        if self.skipped_images:
            message += f". Skipped {self.skipped_images} images"
        return {"message": message, "story_ids": sorted(self.affected_story_ids)}

    def publish(self, news_items: list[NewsItem], source: dict):
        if source.get("parameters", {}).get("COLLECT_IMAGES"):
            result = self.publish_with_images(news_items, source)
            if not self.affected_story_ids:
                raise NoChangeError(result["message"])
            return result["message"]
        news_items = self.process_news_items(news_items, source)
        logger.info(f"Publishing {len(news_items)} news items to core api")
        news_items_dicts = [item.model_dump(mode="json") for item in news_items]
        if not news_items_dicts:
            return None
        if core_response := self.core_api.add_news_items(news_items_dicts):
            self.affected_story_ids.update(core_response.get("story_ids", []))
            if core_response.get("error"):
                if self.affected_story_ids:
                    self.core_api.run_post_collection_bots(source["id"], story_ids=sorted(self.affected_story_ids))
                raise RuntimeError("Cannot add news items")
            core_message = core_response.get("message")
            if core_message == "All news items were skipped":
                raise NoChangeError("All news items were skipped")
            return core_message
        return None

    def publish_or_update_stories(self, story_lists: list[dict], source: dict, story_attribute_key: str | None = None):
        """
        story_lists example: [{title: str, news_items: list[NewsItem]}]
        """
        if not story_lists:
            logger.info(f"No stories to publish from source '{source.get('name')}' with id ({source.get('id')})")
            return None

        if not story_attribute_key:
            news_items = [item for story_list in story_lists for item in story_list["news_items"]]
            return self.publish(news_items, source)

        processed_stories = self.process_news_items_in_stories(story_lists, source, story_attribute_key)

        if story_attribute_key == "misp_event_uuid":
            logger.debug(f"Trying to publish {len(processed_stories)} stories from source {source.get('name'), source.get('id')}")
            if response := self.core_api.add_or_update_for_misp(processed_stories):
                self.affected_story_ids.update(response.get("details", {}).get("story_ids", []))
        else:
            processed_stories = self.set_attr_key_to_existing_stories(processed_stories, story_attribute_key, source)
            for story in processed_stories:
                if (response := self.core_api.add_or_update_story(story)) and (story_id := response.get("story_id") or response.get("id")):
                    self.affected_story_ids.add(story_id)
        return None

    def set_attr_key_to_existing_stories(self, new_stories: list[dict], story_attribute_key: str, source: dict) -> list[dict]:
        # sourcery skip: use-next
        existing_stories = self.core_api.get_stories({"source": source["id"]})
        if not existing_stories:
            return new_stories

        for story in new_stories:
            story_attributes = story.get("attributes", [])
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
