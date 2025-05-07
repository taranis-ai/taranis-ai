from dataclasses import dataclass
from typing import ClassVar, Dict, Any


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
