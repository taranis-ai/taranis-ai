from dataclasses import dataclass
from typing import ClassVar, Dict, Any

from core.log import logger
from core.model.news_item import NewsItem
from core.model.user import User


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

    @classmethod
    def remove_conflict(cls, story_id: str, keep_in_incoming: list, keep_in_existing: list, dissolve: list):
        for news_item_id in keep_in_incoming + keep_in_existing + dissolve:
            key = f"{story_id}:{news_item_id}"
            cls.conflict_store.pop(key, None)

    def to_dict(self) -> dict:
        from core.model.news_item import NewsItem

        title = None
        news_item = NewsItem.get(self.news_item_id)
        if news_item:
            title = news_item.title
        else:
            logger.warning(f"News item {self.news_item_id} not found while resolving conflict display")

        return {
            "incoming_story_id": self.incoming_story_id,
            "news_item_id": self.news_item_id,
            "existing_story_id": self.existing_story_id,
            "incoming_story": self.incoming_story_data,
            "title": title or "Unknown",
        }

    @classmethod
    def remove_conflicting_items_from_story(cls, story: dict, conflicting_ids: list) -> dict:
        if "news_items" in story:
            story["news_items"] = [ni for ni in story["news_items"] if ni.get("id") and ni["id"] not in conflicting_ids]
        return story

    @classmethod
    def remove_dissolve_news_items(cls, dissolve: list):
        from core.model.story import Story

        for news_item_id in dissolve:
            news_item = NewsItem.get(news_item_id)
            if news_item and news_item.story_id:
                Story.remove_news_items_from_story([news_item.story_id], news_item_id)

    @classmethod
    def _regroup_story(cls, incoming_story: dict, keep_in_incoming: list):
        from core.model.story import Story

        news_items_to_regroup = []
        for news_item_id in keep_in_incoming:
            news_item = NewsItem.get(news_item_id)
            if news_item and news_item.story_id:
                result, _ = Story.remove_news_items_from_story([news_item.story_id], news_item_id)
                news_items_to_regroup.append(result.get("new_stories_ids", []))
        Story.group_stories(incoming_story.get("id", "") + news_items_to_regroup)

    @classmethod
    def regroup_news_items(cls, incoming_story: dict, keep_in_incoming: list, dissolve: list):
        cls.remove_dissolve_news_items(dissolve)
        cls._regroup_story(incoming_story, keep_in_incoming)

    @classmethod
    def ingest_incoming_ungroup_internal(cls, data: dict, user: User) -> tuple[dict, int]:
        import core.model.story as story

        if not data:
            return {"error": "Missing story_ids or news_item_ids"}, 400

        incoming_story = data.get("incoming_story")
        story_ids = data.get("existing_story_ids")
        news_item_ids = data.get("incoming_news_item_ids")

        if not story_ids or not news_item_ids or not incoming_story:
            return {"error": "Missing story_ids or news_item_ids or incoming story"}, 400

        story.Story.delete_news_items(news_item_ids)
        story.Story.ungroup_multiple_stories(story_ids, user)

        response, code = story.Story.add(incoming_story)
        if code != 200:
            return {"error": "Failed to ingest incoming story"}, code

        keep_in_incoming = news_item_ids
        keep_in_existing = []
        dissolve = []

        cls.remove_conflict(incoming_story.get("id", ""), keep_in_incoming, keep_in_existing, dissolve)

        return response, 200

    @classmethod
    def remove_by_news_item_ids(cls, news_item_ids: list[str]):
        """Removes all conflicts involving these news_item_ids, regardless of story."""
        logger.debug(f"Removing conflicts for news_item_ids: {news_item_ids}")
        keys_to_remove = [key for key, conflict in cls.conflict_store.items() if conflict.news_item_id in news_item_ids]
        for key in keys_to_remove:
            cls.conflict_store.pop(key, None)

    @classmethod
    def resolve(cls, resolution_data: dict) -> tuple[dict, int]:
        from core.model.story import Story

        incoming_story = resolution_data.get("resolution_data", {}).get("incoming_story", {})
        resolution_items = resolution_data.get("resolution_data", {}).get("news_item_resolutions", [])

        keep_in_incoming = [item["news_item_id"] for item in resolution_items if item["decision"] == "incoming"]
        keep_in_existing = [item["news_item_id"] for item in resolution_items if item["decision"] == "existing"]
        dissolve = [item["news_item_id"] for item in resolution_items if item["decision"] == "dissolve"]

        incoming_story = cls.remove_conflicting_items_from_story(incoming_story, keep_in_existing + dissolve + keep_in_incoming)

        result = Story.add(incoming_story)
        if result[1] == 200:
            cls.regroup_news_items(incoming_story, keep_in_incoming, dissolve)
            return result[0], result[1]

        cls.remove_conflict(incoming_story["id"], keep_in_incoming, keep_in_existing, dissolve)

        return {"message": "The story was successfully submitted."}, 200
