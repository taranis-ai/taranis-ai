import ast
import datetime
from dateutil.parser import isoparse
from pymisp import PyMISP, MISPObject

from worker.core_api import CoreApi
from worker.collectors.base_collector import BaseCollector
from worker.types import NewsItem
from worker.log import logger


class MISPCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.core_api = CoreApi()
        self.type = "MISP_CONNECTOR"
        self.name = "MISP Connector"
        self.description = "Connector for MISP"

        self.proxies = None
        self.headers = {}
        self.connector_id: str

        self.url: str = ""
        self.api_key: str = ""
        self.ssl: bool = False
        self.request_timeout: int
        self.sharing_group_id: str = ""

    def parse_parameters(self, parameters: dict) -> None:
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.ssl = parameters.get("SSL", False)
        self.request_timeout = parameters.get("REQUEST_TIMEOUT", 5)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEADERS", "")
        self.sharing_group_id = parameters.get("SHARING_GROUP_ID", "")
        self.org_id = parameters.get("ORGANISATION_ID", "")

        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def collect(self, source: dict, manual: bool = False) -> None:
        self.parse_parameters(source.get("parameters", ""))

        misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)

        # Note: searching here directly for objects that belong to a sharing group by id using the sharinggroup parameter does not work in 2.5.2.
        # It seems to completely ingnore the sharinggroup parameter and return all objects. The objects controller is poorly documented.
        taranis_objects: list[MISPObject] = misp.search(controller="objects", object_name="taranis-news-item", pythonify=True)  # type: ignore

        logger.debug(f"{taranis_objects=}")
        event_ids = set()
        for obj in taranis_objects:
            event_ids.add(obj.event_id)  # type: ignore
            print(f"Object ID: {obj.id}, Event ID: {obj.event_id}, Object Name: {obj.name}")  # type: ignore

        events: list[dict] = [misp.get_event(event_id) for event_id in event_ids]  # type: ignore
        logger.debug(f"{events=}")
        story_dicts = [
            self.get_story(event, source)
            for event in events
            if (not self.sharing_group_id or str(event.get("Event", {}).get("sharing_group_id")) == str(self.sharing_group_id))
        ]
        story_dicts: list[dict] = [s for s in story_dicts if s is not None]

        for story in story_dicts:
            if self.check_for_proposal_existence(misp, story.get("id", "")):
                story["has_proposals"] = f"{self.url}/events/view/{story.get('id')}"
        logger.debug(f"{story_dicts=}")
        self.publish_or_update_stories(story_dicts, source, story_attribute_key="misp_event_uuid")

    def check_for_proposal_existence(self, misp, event_uuid) -> bool:
        resp = misp._prepare_request("GET", f"shadow_attributes/index/{event_uuid}")
        data: list = misp._check_json_response(resp)
        logger.debug(f"{data=}")
        if data and data[0].get("ShadowAttribute").get("org_id") == self.org_id:
            logger.debug(f"Proposal found for your organisation's event {event_uuid}")
            return True
        return False

    def create_news_item(self, event: dict, source: dict) -> NewsItem:
        logger.debug("Creating news item from MISP event ")
        author = ""
        title = ""
        published: datetime.datetime | None = None
        content = ""
        link = ""
        news_item_id = ""
        orig_source = ""
        story_id = ""
        hash_value = ""
        language = ""
        collected_str = ""
        review = ""
        news_items_properties = event.pop("Attribute", [])
        for item in news_items_properties:
            match item.get("object_relation", ""):
                case "title":
                    title = item.get("value", "")
                case "published":
                    published_str = item.get("value", "")
                    published = (
                        datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%S.%f%z") if published_str else datetime.datetime.now()
                    )
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
                case "collected":
                    collected_str = item.get("value")
                case "review":
                    review = item.get("value")

        return NewsItem(
            source=orig_source,
            id=news_item_id,
            hash=hash_value,
            author=author,
            title=title,
            content=content,
            web_url=link,
            published_date=published,
            story_id=story_id,
            language=language,
            review=review,
            osint_source_id=source.get("id", ""),
            collected_date=datetime.datetime.strptime(collected_str, "%Y-%m-%dT%H:%M:%S.%f%z"),
        )

    def get_internal_osint_source_id(self, osint_source_id: str) -> str:
        osint_source = self.core_api.get_osint_source(osint_source_id)
        if osint_source is not None and osint_source.get("id", ""):
            return osint_source_id
        else:
            return ""

    @staticmethod
    def to_story_dict(story_properties: dict, news_items_list: list[NewsItem], event_uuid: str) -> dict:
        story_properties["news_items"] = news_items_list
        return story_properties

    def get_story_properties_from_story_object(self, event: dict) -> dict:
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

        for item in event.get("Attribute", []):
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

    def get_story(self, event: dict, source: dict) -> dict:
        story_news_items = []
        story_properties = {}
        if event_objects := event.get("Event", {}).get("Object", {}):
            for object in event_objects:
                logger.debug(f"{object=}")
                if object.get("name") == "taranis-story":
                    story_properties = self.get_story_properties_from_story_object(object)
                else:
                    story_news_items.append(self.create_news_item(object, source))

        logger.debug(f"{story_properties=}")
        if not story_properties:
            logger.error(f"The Taranis event is malformed and does not contain the required properties: {story_properties=}")
            raise RuntimeError("The Taranis event is malformed and does not contain the required properties")
        return self.to_story_dict(story_properties, story_news_items, event.get("Event", {}).get("uuid"))


if __name__ == "__main__":
    collector = MISPCollector()
    source = {
        "description": "",
        "icon": None,
        "id": "b583f4ae-7ec3-492a-a36d-ed9cfc0b4a28",
        "last_attempted": None,
        "last_collected": None,
        "last_error_message": None,
        "name": "https",
        "parameters": {
            "ADDITIONAL_HEADERS": "",
            "API_KEY": "bXSZEtpNQL6somSCz08x3IzEnDx1bkM6wwZRd0uZ",
            "PROXY_SERVER": "",
            "REFRESH_INTERVAL": "",
            "URL": "https://localhost",
            "USER_AGENT": "",
            # "SHARING_GROUP_ID": "1",
        },
        "state": -1,
        "type": "misp_connector",
    }
    collector.collect(source)
