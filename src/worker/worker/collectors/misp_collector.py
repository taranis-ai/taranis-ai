import ast
from dateutil.parser import isoparse
from pymisp import PyMISP

from worker.core_api import CoreApi
from worker.collectors.base_collector import BaseCollector
from worker.types import NewsItem
from worker.log import logger


class MISPCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.core_api: CoreApi = CoreApi()
        self.type: str = "MISP_CONNECTOR"
        self.name: str = "MISP Connector"
        self.description: str = "Connector for MISP"

        self.proxies: dict | None = None
        self.headers: dict = {}
        self.connector_id: str

        self.url: str = ""
        self.api_key: str = ""
        self.ssl: bool = False
        self.sharing_group_id: str = ""
        self.org_id: str = ""

    def parse_parameters(self, parameters: dict) -> None:
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.ssl = parameters.get("SSL", False)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEADERS", "")
        self.sharing_group_id = parameters.get("SHARING_GROUP_ID", "")
        self.org_id = parameters.get("ORGANISATION_ID", "")

        if not self.url:
            raise ValueError("Missing URL parameter")
        if not self.api_key:
            raise ValueError("Missing API_KEY parameter")

    def collect(self, source: dict, manual: bool = False) -> None:
        self.parse_parameters(source.get("parameters", ""))
        return self.misp_collector(source)

    def check_for_proposal_existence(self, misp: PyMISP, event_uuid: str) -> bool:
        resp = misp._prepare_request("GET", f"shadow_attributes/index/{event_uuid}")
        data: list = misp._check_json_response(resp)
        if data and data[0].get("ShadowAttribute").get("org_id") == self.org_id:
            logger.debug(f"Proposal found for your organisation's event {event_uuid}")
            return True
        return False

    def create_news_item(self, event: dict, source: dict) -> NewsItem:
        author = ""
        title = ""
        content = ""
        link = ""
        news_item_id = ""
        orig_source = "manual"
        story_id = ""
        hash_value = ""
        language = ""
        review = ""
        news_items_properties = event.pop("Attribute", [])
        for item in news_items_properties:
            match item.get("object_relation", ""):
                case "title":
                    title = item.get("value", "")
                # case "published":
                #     published_str = item.get("value", "")
                #     published = (
                #         datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%S.%f%z") if published_str else datetime.datetime.now()
                #     )
                case "content":
                    content = item.get("value", "")
                case "author":
                    author = item.get("value", "")
                case "link":
                    link = item.get("value", "")
                case "id":
                    news_item_id = item.get("value", "")
                # TODO: Here we need to reuse the hash from the original news item,
                # because only then it is possible to handle conflicts reasonably on the originators side.
                # Obviously, there is still a case when the various Taranis AI instances could ingest
                # the same news item from same/different sources and create different hashes.
                case "hash":
                    hash_value = item.get("value", "")
                case "source":
                    orig_source = item.get("value", "")
                case "story_id":
                    story_id = item.get("value", "")
                case "language":
                    language = item.get("value", "")
                case "review":
                    review = item.get("value")

        logger.debug(f"Creating news item from MISP event with UUID: {news_item_id} story_id: {story_id}")
        return NewsItem(
            source=orig_source,
            id=news_item_id,
            hash=hash_value,
            author=author,
            title=title,
            content=content,
            web_url=link,
            story_id=story_id,
            language=language,
            review=review,
            osint_source_id=source.get("id", ""),
        )

    def get_internal_osint_source_id(self, osint_source_id: str) -> str:
        osint_source = self.core_api.get_osint_source(osint_source_id)
        if osint_source is not None and osint_source.get("id", ""):
            return osint_source_id
        else:
            return ""

    @staticmethod
    def remove_duplicate_news_items(news_items: list[NewsItem]) -> list[NewsItem]:
        hash_list = []
        unique_news_item_list = []
        for news_item in news_items:
            if news_item not in hash_list:
                unique_news_item_list.append(news_item)
                hash_list.append(news_item.hash)
        return unique_news_item_list

    @staticmethod
    def to_story_dict(story_properties: dict, news_items_list: list[NewsItem]) -> dict:
        MISPCollector.remove_duplicate_news_items(news_items_list)
        story_properties["news_items"] = news_items_list
        return story_properties

    def get_story_properties_from_story_object(self, object: dict) -> dict:
        """
        Useful for unit testing.
        If you add or remove a key from here, do the same for the respective object definition file.
        """
        story_properties = {
            "id": None,
            "title": "",
            "comments": "",
            "description": "",
            "summary": "",
            "likes": 0,
            "dislikes": 0,
            "relevance": 0,
            "read": False,
            "important": False,
            "created": None,
            "links": [],
            "tags": [],
            "attributes": [],
        }

        for item in object.get("Attribute", []):
            match item.get("object_relation", ""):
                case "id":
                    story_properties["id"] = item.get("value", None)
                case "title":
                    story_properties["title"] = item.get("value", "")
                case "comments":
                    story_properties["comments"] = item.get("value", "")
                case "description":
                    story_properties["description"] = item.get("value", "")
                case "summary":
                    story_properties["summary"] = item.get("value", "")
                case "important":
                    story_properties["important"] = bool(int(item.get("value", 0)))
                case "read":
                    story_properties["read"] = bool(int(item.get("value", 0)))
                case "created":
                    created_str = item.get("value", "")
                    story_properties["created"] = isoparse(created_str).isoformat()
                case "links":
                    if value := item.get("value", None):
                        story_properties["links"].append(ast.literal_eval(value))
                case "tags":
                    if value := item.get("value", ""):
                        story_properties["tags"].append(ast.literal_eval(value))
                case "attributes":
                    value = item.get("value", "")
                    story_properties["attributes"].append(ast.literal_eval(value))
                case "relevance":
                    story_properties["relevance"] = int(item.get("value", 0))
                case "updated":
                    story_properties["updated"] = item.get("value", None)
                case "likes":
                    story_properties["likes"] = int(item.get("value", 0))
                case "dislikes":
                    story_properties["dislikes"] = int(item.get("value", 0))
        return story_properties

    def get_extended_event_news_items(self, event: dict, misp, source) -> list:
        all_news_items = []
        if extending_events := event.get("Event", {}).get("extensionEvents", {}):
            for extended_event_id, _ in extending_events.items():
                logger.debug(f"Extending event with ID: {extended_event_id}")
                extended_event = misp.get_event(extended_event_id, pythonify=False)
                if not self.is_sharing_group_match(extended_event):
                    logger.debug(f"Skipping extended event with ID {extended_event_id} due to sharing group mismatch")
                    continue
                extended_objects = extended_event.get("Event", {}).get("Object", {})
                _, story_news_items = self.extract_story_data_from_event_objects(extended_objects, source)
                all_news_items.append(story_news_items)

        return all_news_items

    def get_story(self, misp, event: dict, source: dict) -> dict | None:
        story_properties = {}
        story_news_items = []
        extended_news_items = self.get_extended_event_news_items(event, misp, source)

        if event_object_dicts := event.get("Event", {}).get("Object", {}):
            story_properties, news_items = self.extract_story_data_from_event_objects(event_object_dicts, source)
            story_news_items = news_items + extended_news_items  # Keep extended events at the end for deduplication

        if not story_properties:
            logger.error(
                f"The Taranis event is malformed or is just an extended event and does not contain the required properties: {story_properties=}"
            )
            return None
        return self.to_story_dict(story_properties, story_news_items)

    def extract_story_data_from_event_objects(self, event_object_dicts: list[dict], source) -> tuple[dict, list]:  # TODO: check this
        story_news_items = []
        story_properties = {}
        for object in event_object_dicts:
            if object.get("name") == "taranis-story":
                story_properties = self.get_story_properties_from_story_object(object)
            elif object.get("name") == "taranis-news-item":
                news_item = self.create_news_item(object, source)
                story_news_items.append(news_item)
            else:
                logger.warning(f"Unknown object type in MISP event: {object.get('name')}")
        return story_properties, story_news_items

    def get_taranis_event_ids(self, misp) -> set[int]:
        # Note: searching here directly for objects that belong to a sharing group by id using the sharinggroup parameter does not work in 2.5.2.
        # It seems to completely ingnore the sharinggroup parameter and return all objects. The objects controller is poorly documented.
        taranis_objects: list[dict] = misp.search(
            controller="objects", object_name="taranis-news-item", sharinggroup=self.sharing_group_id or None, pythonify=False
        )
        if isinstance(taranis_objects, dict):
            logger.error(f"Error fetching objects from MISP: {taranis_objects.get('message', 'Unknown error')}")
            return set()

        event_ids = set()
        for obj_dict in taranis_objects:
            obj_event_id = obj_dict.get("Object", {}).get("Event", {}).get("id")
            logger.debug(f"Object ID: {obj_dict.get('id')}, Event ID: {obj_event_id}")
            event_ids.add(obj_event_id)
        return event_ids

    def is_sharing_group_match(self, event: dict) -> bool:
        event_sg_id = str(event.get("Event", {}).get("sharing_group_id"))
        return not self.sharing_group_id or event_sg_id == self.sharing_group_id

    def get_taranis_story_dicts(self, misp, events: list[dict], source) -> list[dict]:
        return [story for event in events if self.is_sharing_group_match(event) if (story := self.get_story(misp, event, source)) is not None]

    def set_story_proposal_status(self, misp, story_dicts: list[dict]) -> None:
        for story in story_dicts:
            if self.check_for_proposal_existence(misp, story.get("id", "")):
                story["attributes"].append({"key": "has_proposals", "value": f"{self.url}/events/view/{story.get('id')}"})
            else:
                story["attributes"].append({"key": "has_proposals", "value": ""})

    def misp_collector(self, source: dict) -> None:
        misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)
        event_ids: set[int] = self.get_taranis_event_ids(misp)

        events: list[dict] = [misp.get_event(event_id, extended=False, pythonify=False) for event_id in event_ids]  # type: ignore
        story_dicts = self.get_taranis_story_dicts(misp, events, source)
        logger.info(f"{len(story_dicts)} stories have been collected from MISP")
        self.set_story_proposal_status(misp, story_dicts)

        self.publish_or_update_stories(story_dicts, source, story_attribute_key="misp_event_uuid")
        return None
