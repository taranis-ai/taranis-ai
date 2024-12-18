import hashlib
from pymisp import PyMISP, MISPEvent, MISPObject, exceptions

from worker.collectors.base_collector import BaseCollector
from worker.connectors.definitions.misp_objects import TaranisObject
from worker.log import logger
from worker.types import NewsItem


class MispConnector(BaseCollector):
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
        self.sharing_group: str = ""

    def parse_parameters(self, parameters: dict) -> None:
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.ssl = parameters.get("SSL", False)
        self.request_timeout = parameters.get("REQUEST_TIMEOUT", 5)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEARERS", "")
        self.sharing_group = parameters.get("SHARING_GROUP", "")

        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def execute(self, connector_config: dict, stories: list) -> None:
        if stories:
            self.send(connector_config, stories)
        else:
            self.receive(connector_config)

    def send(self, connector_config: dict, stories: list) -> None:
        logger.debug(f"{connector_config=}")
        self.parse_parameters(connector_config.get("parameters", ""))
        for story in stories:
            self.misp_sender(story)

    def add_objects(self, news_items: dict, event: MISPEvent) -> None:
        for news_item in news_items:
            object_data = {
                "author": news_item.get("author"),
                "content": news_item.get("content"),
                "link": news_item.get("link"),
                "published": news_item.get("published"),
                "title": news_item.get("title"),
            }
            taranis_obj = TaranisObject(parameters=object_data, misp_objects_path_custom="worker/connectors/definitions/objects")
            event.add_object(taranis_obj)

    def create_misp_event(self, story: dict) -> MISPEvent:
        event = MISPEvent()
        event.info = "Description of the event"
        event.distribution = 1
        event.threat_level_id = 4
        event.analysis = 0
        if news_items := story.pop("news_items", None):
            self.add_objects(news_items, event)
        return event

    def send_event_to_misp(self, event: MISPEvent) -> None:
        try:
            misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)

            # debugging
            event_json = event.to_json()
            logger.debug(f"Sending event to MISP: {event_json}")

            created_event: MISPEvent = misp.add_event(event, pythonify=True)  # type: ignore
            logger.info(f"Event created in MISP with UUID: {created_event.uuid}")

        except exceptions.PyMISPError as e:
            logger.error(f"PyMISP exception occurred, but can be misleading (e.g., if received an HTTP/301 response): {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")

    def misp_sender(self, story: dict) -> None:
        event = self.create_misp_event(story)
        self.send_event_to_misp(event)

    ##############################################################################################################

    def receive(self, connector_config: dict) -> None:
        misp_url = connector_config.get("parameters", {}).get("URL", "")
        misp_key = connector_config.get("parameters", {}).get("API_KEY", "")
        misp_verifycert = False
        misp = PyMISP(misp_url, misp_key, misp_verifycert)

        result: list[MISPObject] = misp.search(controller="objects", object_name="news_item", pythonify=True)  # type: ignore
        logger.debug(f"{result=}")
        event_ids = set()
        for obj in result:
            event_ids.add(obj.event_id)  # type: ignore
            print(f"Object ID: {obj.id}, Event ID: {obj.event_id}, Object Name: {obj.name}")  # type: ignore

        events: list[dict] = [misp.get_event(event_id) for event_id in event_ids]  # type: ignore
        logger.debug(f"{events=}")
        stories = [self.get_story_news_items(event, connector_config) for event in events]
        story_dicts = [self.to_story_dict(story) for story in stories]

        self.publish_stories(story_dicts, connector_config)

    def create_news_item(self, event: dict, connector_id: dict) -> NewsItem:
        logger.debug("Creating news item from MISP event ")
        author = ""
        title = ""
        published = ""
        content = ""
        link = ""
        news_items_properties = event.pop("Attribute", [])
        for item in news_items_properties:
            match item.get("object_relation", ""):
                case "title":
                    title = item.get("Attribute", {}).get("value", "")
                case "published":
                    published = item.get("Attribute", {}).get("value", "")
                case "content":
                    content = item.get("Attribute", {}).get("value", "")
                case "author":
                    author = item.get("Attribute", {}).get("value", "")
                case "link":
                    link = item.get("Attribute", {}).get("value", "")
        for_hash: str = author + title + link
        return NewsItem(
            osint_source_id=connector_id["id"],
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

    def get_story_news_items(self, event: dict, connector_config: dict) -> list[NewsItem]:
        story_news_items = []
        if news_items := event.get("Event", {}).get("Object", {}):
            for news_item in news_items:
                logger.debug(f"{news_item=}")
                story_news_items.append(self.create_news_item(news_item, connector_config))

        return story_news_items


def sending():
    # misp = ExpandedPyMISP('https://localhost', 'f10V7k9PUJA6xgwH578Jia7C1lbceBfqTOpeIJqc', False)
    # types_description = misp.describe_types
    # logger.debug(f"{types_description=}")
    connector = MispConnector()
    connector_config = {
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
        },
        "state": -1,
        "type": "misp_connector",
    }
    stories = [
        {
            "comments": "",
            "created": "2024-12-10T07:15:00+01:00",
            "description": 'Adventkalender\nTürchen Nr. 10: Eine kleine Hommage an den Notruf\nDie Weihnachtszeit ist da. Sehen Sie sich täglich das neue Türchen unseres Adventkalenders an und lassen Sie sich von der friedlichen Adventsstimmung verzaubern.\nEine Polizistin und ein Polizist halten Kekse hoch. Sie lächeln, als sie die Zahlen "1-3-3" erkennen – eine kleine Hommage an den Notruf. Die Stimmung und der Duft des frisch gebackenen Gebäcks verbreiteten eine Weihnachtsstimmung. Sie freuen sich auf die besinnliche Zeit, die Momente der Ruhe und des Zusammenhalts inmitten des hektischen Alltags.\nVerfolgen Sie den Adventkalender des Innenministeriums auch auf Facebook und\nInstagram unter "Weiterführende Links".',
            "dislikes": 0,
            "id": "13a3781b-9068-4ae9-a2fa-9da44e4fb230",
            "important": False,
            "likes": 0,
            "links": [],
            "news_items": [
                {
                    "author": "Aktuelles aus dem BM.I",
                    "collected": "2024-12-10T15:37:01.752976+01:00",
                    "content": 'Adventkalender\nTürchen Nr. 10: Eine kleine Hommage an den Notruf\nDie Weihnachtszeit ist da. Sehen Sie sich täglich das neue Türchen unseres Adventkalenders an und lassen Sie sich von der friedlichen Adventsstimmung verzaubern.\nEine Polizistin und ein Polizist halten Kekse hoch. Sie lächeln, als sie die Zahlen "1-3-3" erkennen – eine kleine Hommage an den Notruf. Die Stimmung und der Duft des frisch gebackenen Gebäcks verbreiteten eine Weihnachtsstimmung. Sie freuen sich auf die besinnliche Zeit, die Momente der Ruhe und des Zusammenhalts inmitten des hektischen Alltags.\nVerfolgen Sie den Adventkalender des Innenministeriums auch auf Facebook und\nInstagram unter "Weiterführende Links".',
                    "hash": "be225cdb83c8ab06528af22eabfc28942e272e54694d5f9f5b18ea80993fa580",
                    "id": "335d2d0d-e824-443d-ba8a-68e787b4b3b0",
                    "language": "",
                    "link": "https://www.bmi.gv.at/news.aspx?id=4D737532623078435875493D",
                    "osint_source_id": "9b243209-19ad-4f90-9a7f-b6e957c867c1",
                    "published": "2024-12-10T07:15:00+01:00",
                    "review": "",
                    "source": "https://www.bmi.gv.at/rss/bmi_presse.xml",
                    "story_id": "13a3781b-9068-4ae9-a2fa-9da44e4fb230",
                    "title": "Türchen Nr. 10: Eine kleine Hommage an den Notruf",
                    "updated": "2024-12-10T15:37:01.173551+01:00",
                }
            ],
            "read": False,
            "relevance": 0,
            "summary": "",
            "tags": {},
            "title": "Türchen Nr. 10: Eine kleine Hommage an den Notruf",
            "updated": "2024-12-10T15:37:46.641183+01:00",
        }
    ]
    connector.send(connector_config, stories)


def receiving():
    connector = MispConnector()
    connector_config = {
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
        },
        "state": -1,
        "type": "misp_connector",
    }
    connector.receive(connector_config)


if __name__ == "__main__":
    # sending()
    receiving()
