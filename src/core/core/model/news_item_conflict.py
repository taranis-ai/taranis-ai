from dataclasses import dataclass
from typing import ClassVar, Dict, Any, Iterable, Optional
import copy

from core.log import logger
from core.model.news_item import NewsItem
from core.model.user import User


@dataclass
class NewsItemConflict:
    incoming_story_id: str
    news_item_id: str
    existing_story_id: str
    incoming_story_data: dict[str, Any]
    misp_address: str = ""

    conflict_store: ClassVar[Dict[str, "NewsItemConflict"]] = {}
    story_index: ClassVar[Dict[str, dict[str, Any]]] = {}

    @classmethod
    def _key(cls, incoming_story_id: str, news_item_id: str) -> str:
        return f"{incoming_story_id}:{news_item_id}"

    @classmethod
    def register(
        cls,
        incoming_story_id: str,
        news_item_id: str,
        existing_story_id: str,
        incoming_story_data: dict[str, Any],
        misp_address: str = "",
    ) -> "NewsItemConflict":
        key = cls._key(incoming_story_id, news_item_id)
        story_data_copy = copy.deepcopy(incoming_story_data)

        cls.story_index[incoming_story_id] = story_data_copy

        if key in cls.conflict_store:
            existing_conflict = cls.conflict_store[key]
            existing_conflict.existing_story_id = existing_story_id
            existing_conflict.incoming_story_data = story_data_copy
            logger.debug(f"Updated conflict {key} -> existing_story_id={existing_story_id}")
            return existing_conflict

        conflict = cls(
            incoming_story_id=incoming_story_id,
            news_item_id=news_item_id,
            existing_story_id=existing_story_id,
            incoming_story_data=story_data_copy,
            misp_address=misp_address,
        )
        cls.conflict_store[key] = conflict
        logger.debug(f"Registered conflict {key}")
        return conflict

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
                    incoming_story_data=payload,
                    misp_address=entry.get("misp_address", ""),
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

    @classmethod
    def reevaluate_conflicts(cls, story_ids: Optional[Iterable[str]] = None, story_to_skip: str = ""):
        from core.model.story import Story

        if story_ids is None:
            target_ids = list(cls.story_index.keys())
        else:
            target_ids = list(story_ids)

        if story_to_skip:
            target_ids = [sid for sid in target_ids if sid != story_to_skip]

        logger.debug(f"Reevaluate {len(target_ids)} stories (skip='{story_to_skip or '-'}').")

        for sid in target_ids:
            snapshot = cls.story_index.get(sid)
            if not snapshot:
                logger.debug(f"No snapshot for story {sid}; skipping.")
                continue

            cls.clear_story_conflicts(sid)

            logger.debug(f"Re-adding story {sid} for conflict detection")
            Story.add_or_update(snapshot)

        logger.info("Reevaluation of News Item conflicts ended")

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
            return response, code

        return response, code

    @classmethod
    def ingest_incoming_ungroup_internal_clear_store(cls, data: dict, user: User) -> tuple[dict, int]:
        _ = data.pop("remaining_stories", [])
        incoming_story = data.get("incoming_story") or {}
        incoming_story_id = incoming_story.get("id", "")

        response, code = cls._ingest_incoming_ungroup_internal(data, user)
        removed_count = cls.remove_story(incoming_story_id)

        logger.debug(f"Cleared {removed_count} conflicts and snapshot for story {incoming_story_id}")

        cls.reevaluate_conflicts(story_to_skip=incoming_story_id)

        return response, code

    @classmethod
    def add_news_items_and_clear_from_store(cls, data_json: dict) -> tuple[dict, int]:
        from core.model.story import Story

        incoming_story_id = data_json.get("incoming_story_id") or data_json.get("story_id", "")
        if not incoming_story_id:
            return {"error": "Missing incoming_story_id/story_id"}, 400

        news_items = data_json.get("news_items", [])

        added_ids: list[str] = []
        errors: list[dict] = []

        for news_item_payload in news_items:
            result, status = Story.add_single_news_item(news_item_payload)
            if status == 200:
                added_ids.extend(result.get("news_item_ids", []))
            else:
                logger.error(f"Error ingesting unique news item from conflicts view: {result}")
                errors.append(result)

        cls.remove_story(incoming_story_id)
        cls.reevaluate_conflicts(story_to_skip=incoming_story_id)

        if errors:
            return {"message": "Some news items could not be added", "added_ids": added_ids, "errors": errors}, 207
        return {"message": "News items added successfully", "added_ids": added_ids}, 200
