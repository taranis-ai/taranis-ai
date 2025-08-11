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
    def reevaluate_conflicts(cls, remaining_stories: list, story_to_skip: str = ""):
        from core.model.story import Story

        cls.flush_store()
        logger.debug("Reevaluation of remaining News Item conflicts starts")
        for story in remaining_stories:
            if story.get("id") == story_to_skip:
                logger.debug(f"Skipping story {story} during reevaluation")
                continue
            logger.debug(f"Adding story {story} to news items")
            Story.add_or_update(story)
        logger.info("Reevaluation of remaining News Item conflicts ended")

    def to_dict(self) -> dict:
        title = None
        if news_item := NewsItem.get(self.news_item_id):
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
    def _ingest_incoming_ungroup_internal(cls, data: dict, user: User) -> tuple[dict, int]:
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

        return response, code

    @classmethod
    def ingest_incoming_ungroup_internal_clear_store(cls, data: dict, user: User) -> tuple[dict, int]:
        remaining_stories = data.pop("remaining_stories", [])
        response, code = cls._ingest_incoming_ungroup_internal(data, user)
        if code != 200:
            remaining_stories.append(data.get("incoming_story", {}))
        cls.reevaluate_conflicts(remaining_stories)
        return response, code

    @classmethod
    def add_news_items_and_clear_from_store(cls, data_json: dict) -> tuple[dict, int]:
        from core.model.story import Story

        news_items = data_json.get("news_items", [])
        remaining_stories = data_json.get("remaining_stories", [])
        added_ids = []
        errors = []

        for item in news_items:
            result, status = Story.add_single_news_item(item)
            if status == 200:
                added_ids.extend(result.get("news_item_ids", []))
            else:
                logger.error(f"During ingestion of news items from conflicts view, an error occurred: {result}")
                errors.append(result)

        cls.reevaluate_conflicts(remaining_stories, data_json.get("story_id", ""))
        if errors:
            return {"message": "Some news items could not be added", "errors": errors}, 207
        return {"message": "News items added successfully", "added_ids": added_ids}, 200
