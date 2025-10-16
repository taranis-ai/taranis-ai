import json

from pymisp import MISPEvent
from worker.connectors.definitions.misp_objects import BaseMispObject
from worker.log import logger


DEFAULT_MISP_OBJECTS_PATH = "worker/connectors/definitions/objects"


def get_news_item_object_dict() -> dict:
    return {
        "author": "",
        "content": "",
        "link": "",
        "title": "",
        "hash": "",
        "id": "",
        "language": "",
        "osint_source_id": "",
        "review": "",
        "source": "manual",
        "story_id": "",
    }


def get_story_object_dict() -> dict:
    return {
        "id": "",
        "title": "<no_data>",
        "description": "<no_data>",
        "attributes": {"no_data": {"key": "no_data", "value": "<no_data>"}},
        "comments": "<no_data>",
        "summary": "<no_data>",
        "links": [{"link": "no_data", "news_item_id": "<no_data>"}],
        "tags": {"no_data": {"name": "no_data", "tag_type": "<no_data>"}},
    }


def set_misp_event_uuid_attribute(story: dict) -> None:
    if not story.get("attributes", {}).get("misp_event_uuid"):
        story.setdefault("attributes", {})["misp_event_uuid"] = {
            "key": "misp_event_uuid",
            "value": story.get("id", ""),
        }
    return None


def add_attributes_from_story(story: dict) -> list[str]:
    set_misp_event_uuid_attribute(story)
    results = []

    for key, entry in story.get("attributes", {}).items():
        value = entry.get("value")
        if not value:
            logger.warning(f"Missing 'value' for attribute {key}")
            continue
        results.append(json.dumps({"key": key, "value": value}, sort_keys=True))

    return results


def init_misp_event(event: MISPEvent, data: dict, sharing_group_id: str | None = None, distribution: str | None = None) -> None:
    event.uuid = data.get("id", "")
    event.info = data.get("title", "")
    event.threat_level_id = 4
    event.analysis = 0

    if sharing_group_id:
        event.sharing_group_id = int(sharing_group_id)

    if distribution:
        event.distribution = int(distribution)

    return None


def add_news_item_objects(news_items: list[dict], event: MISPEvent, misp_objects_path_custom: str = DEFAULT_MISP_OBJECTS_PATH) -> None:
    for news_item in news_items:
        news_item.pop("last_change", None)
        object_data = get_news_item_object_dict()
        object_data.update({k: news_item[k] for k in object_data if k in news_item})

        news_item_object = BaseMispObject(
            parameters=object_data,
            template="taranis-news-item",
            misp_objects_path_custom=misp_objects_path_custom,
        )
        event.add_object(news_item_object)

    return None


def prepare_story_for_misp(story: dict) -> dict:
    story.pop("last_change", None)

    object_data = get_story_object_dict()
    object_data.update({key: story[key] for key in object_data if key in story and story[key] not in (None, "", [], {})})

    object_data["links"] = [
        json.dumps({"link": item["link"], "news_item_id": item["news_item_id"]}, sort_keys=True)
        for item in story.get("links", [])
        if isinstance(item, dict) and "link" in item and "news_item_id" in item
    ]

    object_data["tags"] = [
        json.dumps({"name": name, "tag_type": tag["tag_type"]}, sort_keys=True)
        for name, tag in story.get("tags", {}).items()
        if isinstance(tag, dict) and "tag_type" in tag
    ]

    return object_data


def add_story_object(story: dict, event: MISPEvent, misp_objects_path_custom: str = DEFAULT_MISP_OBJECTS_PATH) -> None:
    object_data = prepare_story_for_misp(story)
    object_data["attributes"] = []

    logger.debug(f"Adding story object with data: {object_data}")

    story_object = BaseMispObject(
        parameters=object_data,
        template="taranis-story",
        misp_objects_path_custom=misp_objects_path_custom,
    )

    attribute_list = add_attributes_from_story(story)
    if story.get("attributes"):
        story_object.add_attributes("attributes", *attribute_list)

    event.add_object(story_object)


def add_story_properties_to_event(story: dict, event: MISPEvent, misp_objects_path_custom: str = DEFAULT_MISP_OBJECTS_PATH) -> None:
    if news_items := story.pop("news_items", None):
        add_news_item_objects(news_items, event, misp_objects_path_custom=misp_objects_path_custom)

    add_story_object(story, event, misp_objects_path_custom=misp_objects_path_custom)
