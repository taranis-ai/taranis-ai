import json
from functools import partial
from typing import Any, Callable, Dict, List, Optional

from pymisp import MISPEvent
from worker.connectors.definitions.misp_objects import BaseMispObject
from worker.core_api import CoreApi
from worker.log import logger


class BaseMISPBuilder:
    def __init__(self):
        self.type = "BASE_MISP_CONNECTOR"
        self.name = "Base MISP Connector"
        self.description = "Base abstract type for all MISP connectors"

        self.core_api = CoreApi()

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _generic_processor(entry: Any, required_fields: List[str], key_name_override: Optional[str] = None) -> Optional[Dict]:
        if isinstance(entry, tuple):
            key, value = entry
            payload = value
        else:
            payload = entry
            key = None

        if not isinstance(payload, dict):
            logger.warning(f"Invalid payload: {payload}")
            return None

        result = {}

        for field in required_fields:
            value = payload.get(field)
            if not value:
                logger.warning(f"Missing field '{field}' in {payload}")
                return None
            result[field] = value

        if key_name_override and key is not None:
            result[key_name_override] = key

        return result

    @staticmethod
    def _process_items(data: Any, processor: Callable[..., Optional[Dict]], *processor_args, **processor_kwargs) -> List[str]:
        if isinstance(data, dict):
            items = data.items()
        elif isinstance(data, list):
            items = data
        else:
            logger.warning(f"Unexpected data format: {type(data)}")
            return []

        results = []
        for entry in items:
            if processed := processor(entry, *processor_args, **processor_kwargs):
                results.append(json.dumps(processed, sort_keys=True))
        return results

    def add_attributes_from_story(self, story: dict) -> list:
        self.set_misp_event_uuid_attribute(story)
        attribute_processor = partial(self._generic_processor, required_fields=["value"], key_name_override="key")
        return self._process_items(story.get("attributes", {}), attribute_processor)

    def set_misp_event_uuid_attribute(self, story: dict) -> None:
        if not story.get("attributes", {}).get("misp_event_uuid"):
            story.setdefault("attributes", {})["misp_event_uuid"] = {"key": "misp_event_uuid", "value": story.get("id", "")}

    def create_misp_event(self, data: dict, sharing_group_id: str | None, distribution: str | None) -> MISPEvent:
        event = MISPEvent()
        event.uuid = data.get("id", "")
        event.info = data.get("title", "")
        event.threat_level_id = 4
        event.analysis = 0
        if sharing_group_id:
            event.sharing_group_id = int(sharing_group_id)
        if distribution:
            event.distribution = int(distribution)
        return event

    def add_story_properties_to_event(self, story: dict, event: MISPEvent) -> None:
        if news_items := story.pop("news_items", None):
            self.add_news_item_objects(news_items, event)
        self.add_story_object(story, event)

    def add_news_item_objects(self, news_items: list[dict], event: MISPEvent) -> None:
        for news_item in news_items:
            news_item.pop("last_change", None)
            object_data = self.get_news_item_object_dict()
            object_data.update({k: news_item[k] for k in object_data if k in news_item})

            news_item_object = BaseMispObject(
                parameters=object_data, template="taranis-news-item", misp_objects_path_custom="worker/connectors/definitions/objects"
            )
            event.add_object(news_item_object)

    def add_story_object(self, story: dict, event: MISPEvent) -> None:
        story.pop("last_change", None)

        object_data = self.get_story_object_dict()
        object_data.update(
            {property: story[property] for property in object_data if property in story and story[property] not in (None, "", [], {})}
        )
        object_data["attributes"] = []

        link_processor = partial(self._generic_processor, required_fields=["link", "news_item_id"])
        object_data["links"] = self._process_items(story.get("links", []), link_processor)

        tag_processor = partial(self._generic_processor, required_fields=["tag_type"], key_name_override="name")
        object_data["tags"] = self._process_items(story.get("tags", {}), tag_processor)

        logger.debug(f"Adding story object with data: {object_data}")

        story_object = BaseMispObject(
            parameters=object_data,
            template="taranis-story",
            misp_objects_path_custom="worker/connectors/definitions/objects",
        )
        attribute_list = self.add_attributes_from_story(story)
        if story.get("attributes"):
            story_object.add_attributes("attributes", *attribute_list)
        event.add_object(story_object)
