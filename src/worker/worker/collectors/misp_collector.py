import hashlib
import datetime
from pymisp import PyMISP, MISPObject

from worker.collectors.base_collector import BaseCollector
from worker.types import NewsItem
from worker.log import logger


class MISPCollector(BaseCollector):
    def __init__(self):
        super().__init__()
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
        self.headers = parameters.get("HEARERS", "")
        self.sharing_group_id = parameters.get("SHARING_GROUP_ID", "")

        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def collect(self, source: dict, manual: bool = False) -> None:
        self.parse_parameters(source.get("parameters", ""))

        misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)

        # Note: searching here directly for objects that belong to a sharing group by id using the sharinggroup parameter does not work in 2.5.2.
        # It seems to completely ingnore the sharinggroup parameter and return all objects. The objects controller is poorly documented.
        taranis_objects: list[MISPObject] = misp.search(controller="objects", object_name="news_item", pythonify=True)  # type: ignore

        logger.debug(f"{taranis_objects=}")
        event_ids = set()
        for obj in taranis_objects:
            event_ids.add(obj.event_id)  # type: ignore
            print(f"Object ID: {obj.id}, Event ID: {obj.event_id}, Object Name: {obj.name}")  # type: ignore

        events: list[dict] = [misp.get_event(event_id) for event_id in event_ids]  # type: ignore
        logger.debug(f"{events=}")
        story_dicts = [
            self.to_story_dict(self.get_story_news_items(event, source))
            for event in events
            if (not self.sharing_group_id or str(event.get("Event", {}).get("sharing_group_id")) == str(self.sharing_group_id))
        ]

        self.publish_stories(story_dicts, source)

    def create_news_item(self, event: dict, source: dict) -> NewsItem:
        logger.debug("Creating news item from MISP event ")
        author = ""
        title = ""
        published: datetime.datetime | None = None
        content = ""
        link = ""
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
        for_hash: str = author + title + link
        return NewsItem(
            osint_source_id=source["id"],
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            content=content,
            web_url=link,
            published_date=published,
        )

    @staticmethod
    def to_story_dict(news_items_list: list[NewsItem]) -> dict:
        # Get title and attributes from the first news item (meta item)
        story_title = news_items_list[0].title
        story_attributes = news_items_list[0].attributes
        return {
            "title": story_title,
            "attributes": story_attributes,
            "news_items": news_items_list,
        }

    def get_story_news_items(self, event: dict, source: dict) -> list[NewsItem]:
        story_news_items = []
        if news_items := event.get("Event", {}).get("Object", {}):
            for news_item in news_items:
                logger.debug(f"{news_item=}")
                story_news_items.append(self.create_news_item(news_item, source))

        return story_news_items


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
            "API_KEY": "f10V7k9PUJA6xgwH578Jia7C1lbceBfqTOpeIJqc",
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
