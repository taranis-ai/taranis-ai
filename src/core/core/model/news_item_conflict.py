import copy
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, ClassVar

from models.dashboard import NewsItemConflict as NewsItemConflictModel

from core.log import logger
from core.model.settings import Settings


@dataclass
class NewsItemConflict:
    incoming_story_id: str
    news_item_id: str
    existing_story_id: str
    incoming_story: dict[str, Any]
    misp_address: str | None = None

    conflict_store: ClassVar[dict[str, "NewsItemConflict"]] = {}
    story_index: ClassVar[dict[str, dict[str, Any]]] = {}

    @classmethod
    def register(
        cls,
        incoming_story_id: str,
        news_item_id: str,
        existing_story_id: str,
        incoming_story: dict[str, Any],
        misp_address: str | None = None,
    ) -> dict[str, Any]:
        key = f"{incoming_story_id}:{news_item_id}"
        story_data_copy = copy.deepcopy(incoming_story)
        cls.story_index[incoming_story_id] = story_data_copy

        if key in cls.conflict_store:
            conflict = cls.conflict_store[key]
            conflict.existing_story_id = existing_story_id
            conflict.incoming_story = story_data_copy
            logger.debug(f"Updated conflict {key} -> existing_story_id={existing_story_id}")
        else:
            conflict = cls(
                incoming_story_id=incoming_story_id,
                news_item_id=news_item_id,
                existing_story_id=existing_story_id,
                incoming_story=story_data_copy,
                misp_address=misp_address,
            )
            cls.conflict_store[key] = conflict
            logger.debug(f"Registered conflict {key}")
        return NewsItemConflictModel(
            incoming_story_id=conflict.incoming_story_id,
            news_item_id=conflict.news_item_id,
            existing_story_id=conflict.existing_story_id,
            incoming_story=conflict.incoming_story,
            misp_address=conflict.misp_address or None,
        ).model_dump()

    @classmethod
    def set_for_story(cls, incoming_story_id: str, entries: Iterable[dict[str, Any]]) -> int:
        cls.clear_story_conflicts(incoming_story_id)

        snapshot_set = False
        count = 0

        for entry in entries:
            payload = entry.get("incoming_story_data")
            if isinstance(payload, dict):
                if not snapshot_set:
                    cls.story_index[incoming_story_id] = copy.deepcopy(payload)
                    snapshot_set = True

                cls.register(
                    incoming_story_id=incoming_story_id,
                    news_item_id=entry["news_item_id"],
                    existing_story_id=entry["existing_story_id"],
                    incoming_story=payload,
                    misp_address=entry.get("misp_address"),
                )
                count += 1
            else:
                logger.warning(f"incoming_story_data missing or not a dict for {entry}")

        if not snapshot_set:
            cls.story_index.pop(incoming_story_id, None)

        logger.debug(f"Set {count} conflicts for story {incoming_story_id}")
        return count

    @classmethod
    def clear_story_conflicts(cls, incoming_story_id: str) -> int:
        """Remove only conflicts for this story. Keep snapshot."""
        prefix = f"{incoming_story_id}:"
        to_remove = [conflict_key for conflict_key in cls.conflict_store if conflict_key.startswith(prefix)]
        for key_to_remove in to_remove:
            cls.conflict_store.pop(key_to_remove, None)
        if to_remove:
            logger.debug(f"Cleared {len(to_remove)} conflicts for story {incoming_story_id}")
        return len(to_remove)

    @classmethod
    def remove_story(cls, incoming_story_id: str) -> int:
        """Remove conflicts and snapshot for this story. Returns # conflicts removed."""
        removed = cls.clear_story_conflicts(incoming_story_id)
        cls.story_index.pop(incoming_story_id, None)
        logger.debug(f"Removed snapshot for story {incoming_story_id}")
        return removed

    @classmethod
    def flush_store(cls):
        cls.conflict_store.clear()
        cls.story_index.clear()
        logger.debug("NewsItemConflict: store and index flushed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "incoming_story_id": self.incoming_story_id,
            "news_item_id": self.news_item_id,
            "existing_story_id": self.existing_story_id,
            "incoming_story": self.incoming_story,
            "misp_address": self.misp_address,
        }

    @classmethod
    def enforce_quota(cls):
        """Keep only the most recent N conflicts."""
        settings = Settings.get_settings()
        max_items = int(settings.get("default_news_item_conflict_retention", "200"))
        if len(cls.conflict_store) > max_items:
            excess = len(cls.conflict_store) - max_items
            oldest_keys = list(cls.conflict_store.keys())[:excess]
            for k in oldest_keys:
                cls.conflict_store.pop(k, None)
            logger.info(f"Trimmed {excess} oldest conflicts from News Item conflicts store")
