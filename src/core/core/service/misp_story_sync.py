from typing import Any

from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story


def handle_misp_connector_result(result: dict[str, Any]) -> None:
    if result.get("connector_type") != "MISP_CONNECTOR":
        logger.info(f"Skipping unsupported connector task result: {result.get('connector_type')}")
        return

    connector_id = result.get("connector_id")
    sync_results = result.get("sync_results", [])
    if not isinstance(sync_results, list):
        logger.error("Invalid MISP connector task result: sync_results must be a list")
        return

    for payload in sync_results:
        if payload.get("type") == "misp_auto_update_blocked":
            apply_misp_auto_update_blocked(payload)
        else:
            apply_misp_sync_story_result(
                payload,
                connector_id=connector_id if isinstance(connector_id, str) else None,
                clear_auto_update_status=payload.get("auto_update") is True,
            )


def apply_misp_auto_update_blocked(payload: dict[str, Any]) -> bool:
    story_id = payload.get("story_id")
    proposal_url = payload.get("proposal_url")
    if not isinstance(story_id, str) or not isinstance(proposal_url, str):
        logger.error("Invalid MISP auto-update blocked payload")
        return False
    story = Story.get(story_id)
    if not story or not story.misp_auto_update:
        return False
    sync = story.misp_auto_update
    sync.status = "blocked"
    sync.proposal_url = proposal_url
    sync.pending_until = None
    db.session.commit()
    return True


def apply_misp_sync_story_result(payload: dict[str, Any], connector_id: str | None = None, clear_auto_update_status: bool = False) -> bool:
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
        story.patch_attributes([{"key": "misp_event_uuid", "value": misp_event_uuid}])  # type: ignore TODO: parse attributes before patching
        changed = True

    connector_actor = f"connector_{connector_id}" if connector_id else "external"
    if story.last_change != connector_actor:
        story.last_change = connector_actor
        changed = True

    for news_item_id in news_item_ids:
        if not (news_item := NewsItem.get(news_item_id)):
            logger.warning(f"Could not apply MISP sync result: news item {news_item_id} not found")
            continue
        if news_item.story_id != story.id:
            logger.warning(f"Could not apply MISP sync result: news item {news_item_id} does not belong to story {story_id}")
            continue
        if news_item.last_change != connector_actor:
            news_item.last_change = connector_actor
            news_item.updated = news_item.utcnow()
            changed = True

    sync_state_changed = False
    if clear_auto_update_status and (sync := story.misp_auto_update):
        sync_state_changed = (sync.status, sync.proposal_url, sync.pending_until) != ("enabled", None, None)
        sync.status = "enabled"
        sync.proposal_url = None
        sync.pending_until = None

    if not changed:
        if sync_state_changed:
            db.session.commit()
        return True

    story.updated = story.utcnow()
    story.record_revision(note="misp_sync_story")
    db.session.commit()
    return True
