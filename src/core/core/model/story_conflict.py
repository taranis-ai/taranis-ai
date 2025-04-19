from dataclasses import dataclass
import json
from core.log import logger
from typing import Any
from typing import ClassVar, Dict

from core.model.user import User


@dataclass
class StoryConflict:
    story_id: str
    original: str
    updated: str
    has_proposals: str | None = None
    conflict_store: ClassVar[Dict[str, "StoryConflict"]] = {}

    def resolve(self, resolution: dict, user: User) -> tuple[dict, int]:
        from core.model.story import Story

        try:
            updated_data = json.loads(self.updated)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse updated data for story {self.story_id}: {e}")
            return {"error": "Updated data is not valid JSON", "id": self.story_id}, 400

        updated_data.update(resolution)

        response, code = Story.update(self.story_id, updated_data, user=user, external=True)

        if code == 200:
            StoryConflict.conflict_store.pop(self.story_id, None)
            logger.debug(f"Removed conflict for story {self.story_id} after successful update.")

        return response, code

    @classmethod
    def flush_store(cls):
        cls.conflict_store.clear()
        logger.debug("Conflict store flushed")

    @classmethod
    def get_proposal_count(cls):
        logger.debug(f"with count {len(cls.conflict_store.values())}")
        for conflict in cls.conflict_store.values():
            logger.debug(f"{conflict.has_proposals} ")
        return sum(bool(conflict.has_proposals) for conflict in cls.conflict_store.values())

    @classmethod
    def remove_keys_deep(cls, obj: Any, keys_to_remove: set[str] | None = None) -> Any:
        if keys_to_remove is None:
            keys_to_remove = {"updated", "last_change", "has_proposals"}
        if isinstance(obj, list):
            return [cls.remove_keys_deep(item, keys_to_remove) for item in obj]
        elif isinstance(obj, dict):
            return {key: cls.remove_keys_deep(value, keys_to_remove) for key, value in obj.items() if key not in keys_to_remove}
        return obj

    @classmethod
    def stable_stringify(cls, obj: Any, indent=2) -> str:
        return json.dumps(obj, sort_keys=True, indent=indent)

    @classmethod
    def normalize_data(cls, current_data: dict[str, Any], new_data: dict[str, Any]) -> tuple[str, str]:
        normalized_current = cls.remove_keys_deep(current_data)
        logger.debug(f"{normalized_current=}")
        normalized_new = cls.remove_keys_deep(new_data)
        logger.debug(f"{normalized_new=}")
        return cls.stable_stringify(normalized_current), cls.stable_stringify(normalized_new)
