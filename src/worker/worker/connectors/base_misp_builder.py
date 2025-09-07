import json
from pymisp import MISPEvent
from typing import Callable


from worker.connectors.definitions.misp_objects import BaseMispObject
from worker.core_api import CoreApi
from worker.log import logger


class BaseMispBuilder:
    def __init__(self):
        self.type = "BASE_MISP_CONNECTOR"
        self.name = "Base MISP Connector"
        self.description = "Base abstract type for all MISP connectors"

        self.core_api = CoreApi()

    @staticmethod
    def get_news_item_object_dict() -> dict:
        """
        Useful for unit testing or ensuring consistent keys.
        If you add or remove a key from here, do the same for the respective object definition file.
        """
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
        """
        Useful for unit testing or ensuring consistent keys.
        If you add or remove a key from here, do the same for the respective object definition file.
        """
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
    def _process_items(story: dict, key: str, processor: Callable) -> list:
        """
        Process items from the story, handling both dict and list formats.
        """
        data = story.get(key, {})
        items_list = []

        if isinstance(data, dict):
            logger.debug(f"Processing {len(data)} items from dict for key '{key}'")
            for k, v in data.items():
                processed = processor(k, v)
                if processed is not None:
                    items_list.append(processed)
        elif isinstance(data, list):
            logger.debug(f"Processing {len(data)} items from list for key '{key}'")
            logger.debug(f"Data: {data}")
            for item in data:
                processed = processor(item)
                if processed is not None:
                    items_list.append(processed)
        else:
            logger.warning(f"Unexpected data format for '{key}': {type(data)}")

        return items_list

    @staticmethod
    def _process_attribute(key: str, value_dict: dict) -> str | None:
        """
        Process a single attribute from key and value_dict.
        """
        if not isinstance(value_dict, dict):
            logger.warning(f"Skipping attribute with invalid value: {key} -> {value_dict}")
            return None

        value = value_dict.get("value")
        if value is not None:
            attribute_value = f"{{'key': '{key}', 'value': '{value}'}}"
            logger.debug(f"Adding attribute: {attribute_value}")
            return attribute_value
        else:
            logger.warning(f"Skipping attribute with missing value: {key}")
            return None

    @staticmethod
    def _process_link(link_item: dict) -> str | None:
        """
        Process a single link dict into its string representation.
        """
        link = link_item.get("link", "")
        news_item_id = link_item.get("news_item_id", "")
        if link and news_item_id:
            link_value = f"{{'link': '{link}', 'news_item_id': '{news_item_id}'}}"
            logger.debug(f"Adding link: {link_value}")
            return link_value
        else:
            logger.warning(f"Skipping link with missing data: {link_item}")
            return None

    @staticmethod
    def _process_tags(tag_dict: dict) -> str | None:
        """
        Process a single tag from key and value_dict.
        """
        if not isinstance(tag_dict, dict):
            logger.warning(f"Skipping tag with invalid value: {tag_dict.get('name', 'unknown')} -> {tag_dict}")
            return None

        tag_type = tag_dict.get("tag_type", "misc")
        tag_json = json.dumps({"name": tag_dict.get("name", ""), "tag_type": tag_type})
        logger.debug(f"Adding tag: {tag_json}")
        return tag_json

    def add_attributes_from_story(self, story: dict) -> list:
        """
        Process attributes from the story, ensuring internal metadata (like misp_event_uuid)
        is added and only valid attributes are included.
        """
        self.set_misp_event_uuid_attribute(story)
        return self._process_items(story, "attributes", self._process_attribute)

    def set_misp_event_uuid_attribute(self, story: dict) -> None:
        """
        Ensure the story has a 'misp_event_uuid' attribute so that the system can determine if it is
        an update or a new event.
        """
        if not story.get("attributes", {}).get("misp_event_uuid"):
            story.get("attributes", {})["misp_event_uuid"] = {"key": "misp_event_uuid", "value": story.get("id", "")}

    def create_misp_event(self, data: dict, sharing_group_id: str | None, distribution: str | None) -> MISPEvent:
        """
        Create a MISPEvent from the 'story' dictionary.
        """
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
        """
        For each news item in 'news_items', create a TaranisObject and add it to the event.
        """
        for news_item in news_items:
            news_item.pop("last_change", None)  # key intended for internal use only
            object_data = self.get_news_item_object_dict()
            # sourcery skip: dict-assign-update-to-union
            object_data.update({k: news_item[k] for k in object_data if k in news_item})  # only keep keys that are in the object_data dict

            news_item_object = BaseMispObject(
                parameters=object_data, template="taranis-news-item", misp_objects_path_custom="worker/connectors/definitions/objects"
            )
            event.add_object(news_item_object)

    def add_story_object(self, story: dict, event: MISPEvent) -> None:
        """
        Create a TaranisObject for the story itself, add attributes, links, and tags from the story,
        and attach it to the event with all data correctly stored under their respective keys.
        """
        # Remove internal keys not meant for external processing
        story.pop("last_change", None)

        object_data = self.get_story_object_dict()
        object_data.update(
            {property: story[property] for property in object_data if property in story and story[property] not in (None, "", [], {})}
        )
        object_data["attributes"] = []

        links_to_process = story.get("links") or object_data["links"]
        object_data["links"] = self._process_items({"links": links_to_process}, "links", self._process_link)

        tags_to_process = story.get("tags") or object_data["tags"]
        object_data["tags"] = self._process_items({"tags": tags_to_process}, "tags", self._process_tags)

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
