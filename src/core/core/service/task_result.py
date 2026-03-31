from datetime import datetime
from typing import Any

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.product import Product
from core.model.story import Story
from core.model.token_blacklist import TokenBlacklist
from core.model.word_list import WordList
from core.service.news_item_tag import NewsItemTagService


def _get_dict_result(result: dict[str, Any] | str, task_name: str) -> dict[str, Any] | None:
    if isinstance(result, dict):
        return result

    logger.error(f"Invalid {task_name} task result type: {type(result)}")
    return None


def handle_task_specific_result(task_id: str, result: dict | str, _status: str, task_name: str | None = None):
    task_name = task_name or ""

    if task_id.startswith("gather_word_list") or task_name == "gather_word_list":
        if not (result_dict := _get_dict_result(result, "gather_word_list")):
            return

        content = result_dict.get("content")
        content_type = result_dict.get("content_type")
        word_list_id = result_dict.get("word_list_id")
        if not isinstance(content, str) or not isinstance(content_type, str) or not isinstance(word_list_id, int):
            logger.error("Invalid gather_word_list task result payload")
            return

        WordList.update_word_list(content=content, content_type=content_type, word_list_id=word_list_id)
    elif task_id.startswith("cleanup_token_blacklist") or task_name == "cleanup_token_blacklist":
        TokenBlacklist.delete_older(datetime.now() - Config.JWT_ACCESS_TOKEN_EXPIRES)
    elif task_id.startswith("presenter_task") or task_name == "presenter_task":
        if not (result_dict := _get_dict_result(result, "presenter_task")):
            return

        rendered_product = result_dict.get("render_result")
        product_id = result_dict.get("product_id")
        if not isinstance(product_id, str) or not isinstance(rendered_product, str):
            logger.error(f"Product {product_id} not found or no render result")
            return

        Product.update_render_for_id(product_id, rendered_product)
    elif task_id.startswith("collect_") or task_name == "collector_task":
        logger.info(f"Collector task {task_id} completed with result: {result}")
    elif task_id.startswith("bot") or task_name == "bot_task":
        if not (result_dict := _get_dict_result(result, "bot_task")):
            return

        bot_result = result_dict.get("result")
        if not isinstance(bot_result, dict):
            logger.error("Invalid bot task result payload")
            return

        if bot_result.get("error") or bot_result.get("message"):
            logger.error(bot_result.get("error") or bot_result.get("message"))
            return

        bot_type = result_dict.get("bot_type", "")
        tagging_bots = ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"]
        if bot_type in tagging_bots:
            NewsItemTagService.set_found_bot_tags(result_dict, change_by_bot=True)

        NewsItemTagService.set_bot_execution_attribute(result_dict)
    elif task_name == "connector_task":
        handle_connector_result(result)


def handle_connector_result(result: dict[str, Any] | str) -> None:
    if not isinstance(result, dict):
        logger.error(f"Invalid connector task result type: {type(result)}")
        return

    if result.get("connector_type") != "MISP_CONNECTOR":
        logger.info(f"Skipping unsupported connector task result: {result.get('connector_type')}")
        return

    internal_results = result.get("result", [])
    if not isinstance(internal_results, list):
        logger.error("Invalid MISP connector task result: result must be a list")
        return

    for payload in internal_results:
        handle_internal_result(payload)


def handle_internal_result(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        logger.error(f"Invalid internal result payload type: {type(payload)}")
        return False

    if payload.get("type") != "misp_sync_story":
        logger.warning(f"Unsupported internal result type: {payload.get('type')}")
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
