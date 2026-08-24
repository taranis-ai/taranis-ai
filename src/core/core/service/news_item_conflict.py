from collections.abc import Iterable

from core.log import logger
from core.model.news_item_conflict import NewsItemConflict
from core.model.story import Story
from core.model.user import User
from core.service.misp_auto_update import cancel_misp_auto_update_jobs


class NewsItemConflictService:
    @staticmethod
    def reevaluate_conflicts(story_ids: Iterable[str] | None = None, story_to_skip: str = "") -> None:
        target_ids = list(NewsItemConflict.story_index if story_ids is None else story_ids)
        if story_to_skip:
            target_ids = [story_id for story_id in target_ids if story_id != story_to_skip]

        logger.debug(f"Reevaluate {len(target_ids)} stories (skip='{story_to_skip or '-'}').")
        for story_id in target_ids:
            snapshot = NewsItemConflict.story_index.get(story_id)
            if not snapshot:
                logger.debug(f"No snapshot for story {story_id}; skipping.")
                continue

            NewsItemConflict.clear_story_conflicts(story_id)
            logger.debug(f"Re-adding story {story_id} for conflict detection")
            Story.add_or_update(snapshot)

        logger.info("Reevaluation of News Item conflicts ended")

    @classmethod
    def ingest_incoming_ungroup_internal_clear_store(cls, data: dict, user: User) -> tuple[dict, int]:
        _ = data.pop("remaining_stories", [])
        incoming_story = data.get("incoming_story") or {}
        incoming_story_id = incoming_story.get("id", "")

        if not data:
            response, code = {"error": "Missing story_ids or news_item_ids"}, 400
        else:
            story_ids: list[str] = data.get("existing_story_ids", [])
            news_item_ids: list[str] = data.get("incoming_news_item_ids", [])
            if not story_ids or not news_item_ids or not incoming_story:
                response, code = {"error": "Missing story_ids or news_item_ids or incoming story"}, 400
            else:
                Story.delete_news_items(news_item_ids)
                Story.ungroup_multiple_stories(story_ids, user)
                response, code = Story.add(incoming_story)
                cancel_misp_auto_update_jobs(story_id for story_id in story_ids if Story.get(story_id) is None)

        removed_count = NewsItemConflict.remove_story(incoming_story_id)
        logger.debug(f"Cleared {removed_count} conflicts and snapshot for story {incoming_story_id}")
        cls.reevaluate_conflicts(story_to_skip=incoming_story_id)
        return response, code

    @classmethod
    def add_news_items_and_clear_from_store(cls, data_json: dict) -> tuple[dict, int]:
        incoming_story_id = data_json.get("incoming_story_id") or data_json.get("story_id", "")
        if not incoming_story_id:
            return {"error": "Missing incoming_story_id/story_id"}, 400

        added_ids: list[str] = []
        errors: list[dict] = []
        for news_item_payload in data_json.get("news_items", []):
            result, status = Story.add_single_news_item(news_item_payload)
            if status == 200:
                added_ids.extend(result.get("news_item_ids", []))
            else:
                logger.error(f"Error ingesting unique news item from conflicts view: {result}")
                errors.append(result)

        NewsItemConflict.remove_story(incoming_story_id)
        cls.reevaluate_conflicts(story_to_skip=incoming_story_id)

        if errors:
            return {"message": "Some news items could not be added", "added_ids": added_ids, "errors": errors}, 207
        return {"message": "News items added successfully", "added_ids": added_ids}, 200
