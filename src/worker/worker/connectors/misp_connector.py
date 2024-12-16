import hashlib
import datetime
from pymisp import ExpandedPyMISP, MISPEvent

from worker.connectors.definitions.misp_objects import TaranisObject
from worker.core_api import CoreApi
from worker.log import logger
from worker.types import NewsItem


class MispConnector:
    def __init__(self):
        self.type = "MISP_CONNECTOR"
        self.name = "MISP Connector"
        self.description = "Connector for MISP"
        self.core_api = CoreApi()

        self.proxies = None
        self.headers = {}
        self.connector_id: str

        self.url: str = ""
        self.api_key: str = ""
        self.misp_verifycert: bool = False

    def parse_parameters(self, parameters: dict) -> None:
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.misp_verifycert = parameters.get("MISP_VERIFYCERT", False)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEARERS", "")

        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def send(self, connector_config: dict, stories: list) -> None:
        logger.debug(f"{connector_config=}")
        self.parse_parameters(connector_config.get("parameters", ""))
        for story in stories:
            self.misp_sender(story)

        logger.info(f"Sending story to MISP connecector {connector_config.get('id')}")

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

    def send_event_to_misp(self, misp: ExpandedPyMISP, event: MISPEvent) -> None:
        event_json = event.to_json()
        logger.debug(f"Sending event to MISP: {event_json}")
        created_event = misp.add_event(event)
        logger.info(f"Event created in MISP with UUID: {created_event['Event']['uuid']}")

    def misp_sender(self, story: dict) -> None:
        event = self.create_misp_event(story)
        misp = ExpandedPyMISP(self.url, self.api_key, self.misp_verifycert)
        self.send_event_to_misp(misp, event)
        logger.info("Sending story to MISP")

    def create_news_item(self, source, event: dict) -> NewsItem:
        logger.debug("Creating news item from MISP event ")
        logger.debug(f"{event=}")
        author = event.get("author", "")
        title = event.get("title", "")
        link = event.get("link", "")
        for_hash: str = author + title + link
        return NewsItem(
            osint_source_id=source["id"],
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            author=author,
            title=title,
            content=event.get("content", ""),
            web_url=link,
            published_date=datetime.datetime.now(),
            language=source.get("language", ""),
        )

    def receive(self, connector_config: dict) -> None:
        misp_url = connector_config.get("parameters", {}).get("URL", "")
        misp_key = connector_config.get("parameters", {}).get("API_KEY", "")
        misp_verifycert = False
        misp = ExpandedPyMISP(misp_url, misp_key, misp_verifycert)

        result = misp.search(controller="objects", object_name="news_item", pythonify=True)
        event_ids = set()
        for obj in result:
            event_ids.add(obj.event_id)
            print(f"Object ID: {obj.id}, Event ID: {obj.event_id}, Object Name: {obj.name}")

        events = [misp.get_event(event_id) for event_id in event_ids]
        stories = [self.create_news_item(connector_config, event) for event in events]
        from worker.collectors.base_collector import BaseCollector

        BaseCollector.publish_stories(stories, connector_config)


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
