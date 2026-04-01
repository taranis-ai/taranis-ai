from typing import Any

from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story


def handle_misp_connector_result(result: dict[str, Any] | str) -> None:
    if not isinstance(result, dict):
        logger.error(f"Invalid connector task result type: {type(result)}")
        return

    if result.get("connector_type") != "MISP_CONNECTOR":
        logger.info(f"Skipping unsupported connector task result: {result.get('connector_type')}")
        return

    sync_results = result.get("sync_results", [])
    if not isinstance(sync_results, list):
        logger.error("Invalid MISP connector task result: sync_results must be a list")
        return

    for payload in sync_results:
        apply_misp_sync_story_result(payload)


def apply_misp_sync_story_result(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        logger.error(f"Invalid MISP sync payload type: {type(payload)}")
        return False

    if payload.get("type") != "misp_sync_story":
        logger.warning(f"Unsupported MISP sync payload type: {payload.get('type')}")
        return False

    story_id = payload.get("story_id")
    misp_event_uuid = payload.get("misp_event_uuid")
    news_item_ids = payload.get("news_item_ids_to_mark_external", [])

    if not isinstance(story_id, str) or not story_id:
        logger.error("Invalid MISP sync payload: missing story_id")
        return False
    if not isinstance(misp_event_uuid, str) or not misp_event_uuid:
        logger.error("Invalid MISP sync payload: missing misp_event_uuid")
        return False
    if not isinstance(news_item_ids, list) or any(not isinstance(item_id, str) or not item_id for item_id in news_item_ids):
        logger.error("Invalid MISP sync payload: news_item_ids_to_mark_external must be a list of non-empty strings")
        return False

    if not (story := Story.get(story_id)):
        logger.error(f"Could not apply MISP sync result: story {story_id} not found")
        return False

    changed = False
    if current_attr := story.find_attribute_by_key("misp_event_uuid"):
        if current_attr.value != misp_event_uuid:
            current_attr.value = misp_event_uuid
            changed = True
    else:
        story.patch_attributes([{"key": "misp_event_uuid", "value": misp_event_uuid}])
        changed = True

    if story.last_change != "external":
        story.last_change = "external"
        changed = True

    for news_item_id in news_item_ids:
        if not (news_item := NewsItem.get(news_item_id)):
            logger.warning(f"Could not apply MISP sync result: news item {news_item_id} not found")
            continue
        if news_item.story_id != story.id:
            logger.warning(f"Could not apply MISP sync result: news item {news_item_id} does not belong to story {story_id}")
            continue
        if news_item.last_change != "external":
            news_item.last_change = "external"
            news_item.updated = news_item.utcnow()
            changed = True

    if not changed:
        return True

    story.updated = story.utcnow()
    story.record_revision(note="misp_sync_story")
    db.session.commit()
    return True
