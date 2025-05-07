from dataclasses import dataclass
from typing import ClassVar, Dict, Any

from core.log import logger
from core.model.news_item import NewsItem


@dataclass
class NewsItemConflict:
    incoming_story_id: str
    news_item_id: str
    existing_story_id: str
    incoming_story_data: dict[str, Any]

    conflict_store: ClassVar[Dict[str, "NewsItemConflict"]] = {}

    @classmethod
    def register(
        cls, incoming_story_id: str, news_item_id: str, existing_story_id: str, incoming_story_data: dict[str, Any]
    ) -> "NewsItemConflict":
        conflict = cls(
            incoming_story_id=incoming_story_id,
            news_item_id=news_item_id,
            existing_story_id=existing_story_id,
            incoming_story_data=incoming_story_data,
        )
        key = f"{incoming_story_id}:{news_item_id}"
        cls.conflict_store[key] = conflict
        return conflict

    @classmethod
    def flush_store(cls):
        cls.conflict_store.clear()

    def to_dict(self) -> dict:
        return {
            "incoming_story_id": self.incoming_story_id,
            "news_item_id": self.news_item_id,
            "existing_story_id": self.existing_story_id,
            "incoming_story": self.incoming_story_data,
        }

    @classmethod
    def remove_conflicting_items_from_story(cls, story: dict, conflicting_ids: list) -> dict:
        if "news_items" in story:
            story["news_items"] = [ni for ni in story["news_items"] if ni.get("id") and ni["id"] not in conflicting_ids]
        return story

    @classmethod
    def resolve(cls, resolution_data: dict) -> tuple[dict, int]:
        from core.model.story import Story

        logger.debug(f"Resolving conflict with data: {resolution_data}")
        incoming_story = resolution_data.get("resolution_data", {}).get("incoming_story", {})
        checked_news_item_ids = resolution_data.get("resolution_data", {}).get("checked_news_items", [])
        logger.debug(f"Checked news item IDs: {checked_news_item_ids}")
        unchecked_news_item_ids = resolution_data.get("resolution_data", {}).get("unchecked_news_items", [])
        logger.debug(f"Unchecked news item IDs: {unchecked_news_item_ids}")
        conflicting_ids = checked_news_item_ids + unchecked_news_item_ids
        clean_story = cls.remove_conflicting_items_from_story(incoming_story, conflicting_ids)
        logger.debug(f"Cleaned story: {clean_story}")
        result = Story.add(clean_story)
        if result[1] != 200:
            return result[0], result[1]
        story_ids = []
        for id in checked_news_item_ids:
            if news_item := NewsItem.get(id):
                story_ids.append(news_item.story_id)

        result = Story.group_stories([incoming_story.get("id")] + story_ids)
        for news_item_id in checked_news_item_ids + unchecked_news_item_ids:
            key = f"{incoming_story.get('id')}:{news_item_id}"
            cls.conflict_store.pop(key, None)
        return (result[0], result[1]) if result[1] != 200 else ({"message": "The story was successfully submitted."}, 200)
