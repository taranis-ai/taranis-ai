from pymisp import PyMISP, MISPEvent, exceptions

from worker.connectors.definitions.misp_objects import TaranisObject
from worker.core_api import CoreApi
from worker.log import logger


class MISPConnector:
    def __init__(self):
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
        self.distribution: str = "1"

    def parse_parameters(self, parameters: dict) -> None:
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.ssl = parameters.get("SSL", False)
        self.request_timeout = parameters.get("REQUEST_TIMEOUT", 5)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEARERS", "")
        self.sharing_group_id = parameters.get("SHARING_GROUP_ID", "")
        self.distribution = parameters.get("DISTRIBUTION", "")
        if not self.distribution and self.sharing_group_id:
            self.distribution = "4"
        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def execute(self, connector_config: dict, stories: list) -> None:
        logger.debug(f"{connector_config=}")
        self.parse_parameters(connector_config.get("parameters", ""))
        for story in stories:
            misp_event_uuid = self.get_event_uuid_from_story(story)
            self.misp_sender(story, misp_event_uuid)

    def get_event_uuid_from_story(self, story: dict) -> str | None:
        story_attributes = story.get("attributes", [])
        return next(
            (attribute.get("value") for attribute in story_attributes if attribute.get("key") == "misp_event_uuid"),
            None,
        )

    @staticmethod
    def get_news_item_object_dict() -> dict:
        """Useful for unit testing of the template keys"""
        return {
            "author": "",
            "content": "",
            "link": "",
            "published": "",
            "title": "",
            "collected": "",
            "hash": "",
            "id": "",
            "language": "",
            "osint_source_id": "",
            "review": "",
            "source": "",
            "story_id": "",
            "updated": "",
        }

    def add_objects(self, news_items: dict, event: MISPEvent) -> None:
        object_data = MISPConnector.get_news_item_object_dict()
        for news_item in news_items:
            object_data["author"] = news_item.get("author")
            object_data["content"] = news_item.get("content")
            object_data["link"] = news_item.get("link")
            object_data["published"] = news_item.get("published")
            object_data["title"] = news_item.get("title")
            object_data["collected"] = news_item.get("collected")
            object_data["hash"] = news_item.get("hash")
            object_data["id"] = news_item.get("id")
            object_data["language"] = news_item.get("language")
            object_data["osint_source_id"] = news_item.get("osint_source_id")
            object_data["review"] = news_item.get("review")
            object_data["source"] = news_item.get("source")
            object_data["story_id"] = news_item.get("story_id")
            object_data["updated"] = news_item.get("updated")
            taranis_obj = TaranisObject(parameters=object_data, misp_objects_path_custom="worker/connectors/definitions/objects")
            event.add_object(taranis_obj)

    def create_misp_event(self, story: dict) -> MISPEvent:
        event = MISPEvent()
        event.info = story.get("title", "")
        event.threat_level_id = 4
        event.analysis = 0
        if self.sharing_group_id:
            event.sharing_group_id = int(self.sharing_group_id)
        if self.distribution:
            event.distribution = int(self.distribution)

        self.add_event_attributes(story, event)
        return event

    def get_event_id_by_uuid(self, misp, event_uuid: str) -> int | None:
        if results := misp.search(controller="events", uuid=event_uuid, pythonify=True):
            logger.debug(f"Event to update exists: {results}")
            return results[0].id
        else:
            logger.error(f"Requested event to update with UUID: {event_uuid} does not exist")
            return None

    def add_event_attributes(self, story: dict, event: MISPEvent):
        if news_items := story.pop("news_items", None):
            self.add_objects(news_items, event)

    def add_misp_event(self, misp: PyMISP, event) -> MISPEvent | None:
        created_event: MISPEvent | dict = misp.add_event(event, pythonify=True)
        return None if isinstance(created_event, dict) else created_event

    def update_misp_event(self, misp, event: MISPEvent, misp_event_uuid) -> MISPEvent | None:
        if event_id := self.get_event_id_by_uuid(misp, misp_event_uuid):
            event.uuid = misp_event_uuid
            updated_event: MISPEvent | dict = misp.update_event(event, event_id=event_id, pythonify=True)
            return None if isinstance(updated_event, dict) else updated_event
        return None

    def send_event_to_misp(self, event: MISPEvent, misp_event_uuid: str | None = None) -> str | None:
        try:
            misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)

            # debugging
            event_json = event.to_json()

            logger.debug(f"Sending event to MISP: {event_json}")
            if misp_event_uuid:
                if result := self.update_misp_event(misp, event, misp_event_uuid):
                    logger.info(f"Event with UUID: {result.uuid} was updated in MISP")
                    return result.uuid
                logger.error("Failed to update event in MISP")

            if created_event := self.add_misp_event(misp, event):
                logger.info(f"Event was created in MISP with UUID: {created_event.uuid}")
                return created_event.uuid
            logger.error("Failed to create event in MISP")
            return None
        except exceptions.PyMISPError as e:
            logger.error(f"PyMISP exception occurred, but can be misleading (e.g., if received an HTTP/301 response): {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")

    def misp_sender(self, story: dict, misp_event_uuid: str | None = None) -> None:
        event = self.create_misp_event(story)
        if event_uuid := self.send_event_to_misp(event, misp_event_uuid):
            self.core_api.api_patch(
                f"/bots/story/{story.get("id", "")}/attributes",
                {"key": "misp_event_uuid", "value": f"{event_uuid}"},
            )


def sending():
    connector = MISPConnector()
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
            "SHARING_GROUP_ID": "1",
            "DISTRIBUTION": "",
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
    connector.execute(connector_config, stories)


if __name__ == "__main__":
    sending()
