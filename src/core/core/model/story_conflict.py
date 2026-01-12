import json
from dataclasses import dataclass
from typing import Any, ClassVar

from models.dashboard import StoryConflict as StoryConflictModel

from core.log import logger
from core.model.news_item_conflict import NewsItemConflict
from core.model.settings import Settings
from core.model.user import User


STORY_CONFLICT_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "attributes",
        "comments",
        "description",
        "id",
        "news_items",
        "summary",
        "tags",
        "title",
        "author",
        "content",
        "hash",
        "link",
        "review",
        "source",
    }
)


@dataclass
class StoryConflict:
    story_id: str
    existing_story: str
    incoming_story: str
    has_proposals: str | None = None
    conflict_store: ClassVar[dict[str, "StoryConflict"]] = {}

    def to_dict(self) -> dict[str, Any]:
        return StoryConflictModel(
            story_id=self.story_id,
            existing_story=self.existing_story,
            incoming_story=self.incoming_story,
            has_proposals=self.has_proposals,
        ).model_dump()

    @classmethod
    def get_conflict_count(cls) -> int:
        return len(set(StoryConflict.conflict_store.keys()))

    def resolve(self, resolution: dict[str, Any], user: User) -> tuple[dict[str, Any], int]:
        from core.model.story import Story

        try:
            updated_data: dict[str, Any] = json.loads(self.incoming_story)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse updated data for story {self.story_id}: {e}")
            return {"error": "Updated data is not valid JSON", "id": self.story_id}, 400

        # @param: resolution - comes without certain Story keys (e.g. story ID), it needs to be merged back
        updated_data |= resolution

        story = Story.get(self.story_id)
        if not story:
            logger.error(f"Story with id {self.story_id} not found for resolution.")
            return {"error": "Story not found", "id": self.story_id}, 404

        response, code = story.add_or_update_for_misp([updated_data], force=True)

        if code == 200:
            StoryConflict.conflict_store.pop(self.story_id, None)
            logger.debug(f"Removed conflict for story {self.story_id} after successful update.")
        elif code == 409:
            StoryConflict.conflict_store.pop(self.story_id, None)
            NewsItemConflict.enforce_quota()
            logger.warning(f"Conflict resolution for story {self.story_id}.")

        return response, code

    @classmethod
    def flush_store(cls) -> None:
        cls.conflict_store.clear()
        logger.debug("Conflict store flushed")

    @classmethod
    def get_proposal_count(cls) -> int:
        logger.debug(f"with count {len(cls.conflict_store.values())}")
        return sum(bool(conflict.has_proposals) for conflict in cls.conflict_store.values())

    @classmethod
    def keep_keys_deep(cls, obj: Any, allowed_keys: frozenset[str]) -> Any:
        if isinstance(obj, list):
            return [cls.keep_keys_deep(item, allowed_keys) for item in obj]

        if isinstance(obj, dict):
            return {key: cls.keep_keys_deep(value, allowed_keys) for key, value in obj.items() if key in allowed_keys}

        return obj

    @classmethod
    def stable_stringify(cls, obj: Any, indent: int = 2) -> str:
        return json.dumps(obj, sort_keys=True, indent=indent, ensure_ascii=False)

    @classmethod
    def normalize_data(cls, current_data: dict[str, Any], new_data: dict[str, Any]) -> tuple[str, str]:
        normalized_current = cls.keep_keys_deep(current_data, STORY_CONFLICT_ALLOWED_KEYS)
        normalized_new = cls.keep_keys_deep(new_data, STORY_CONFLICT_ALLOWED_KEYS)
        return cls.stable_stringify(normalized_current), cls.stable_stringify(normalized_new)

    @classmethod
    def enforce_quota(cls) -> None:
        """Keep only the most recent N conflicts."""
        settings = Settings.get_settings()
        max_items = int(settings.get("default_story_conflict_retention", "200"))

        if len(cls.conflict_store) > max_items:
            excess = len(cls.conflict_store) - max_items

            # NOTE: dict insertion order == insertion order (Python 3.7+)
            oldest_keys = list(cls.conflict_store.keys())[:excess]
            for k in oldest_keys:
                cls.conflict_store.pop(k, None)

            logger.info(f"Trimmed {excess} oldest conflicts from Story conflicts store")
