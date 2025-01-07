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
            existing_event_essentials = self.get_existing_event_essentials(story)
            self.misp_sender(story, existing_event_essentials=existing_event_essentials)

    def get_existing_event_essentials(self, story: dict) -> dict | None:
        story_attributes = story.get("attributes", [])
        misp_event_id = next(
            (int(attribute.get("value")) for attribute in story_attributes if attribute.get("key") == "misp_event_id"),
            None,
        )
        misp_event_uuid = next(
            (attribute.get("value") for attribute in story_attributes if attribute.get("key") == "misp_event_uuid"),
            None,
        )
        if misp_event_id is None or misp_event_uuid is None:
            return None
        return {"misp_event_id": misp_event_id, "misp_event_uuid": misp_event_uuid}

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
        return event

    def add_event_attributes(self, story: dict, event: MISPEvent) -> None:
        if news_items := story.pop("news_items", None):
            self.add_objects(news_items, event)

    def send_event_to_misp(self, event: MISPEvent, existing_event_essentials: dict | None, story: dict) -> int | None:
        try:
            misp = PyMISP(url=self.url, key=self.api_key, ssl=self.ssl, proxies=self.proxies, http_headers=self.headers)

            # debugging
            event_json = event.to_json()
            logger.debug(f"Sending event to MISP: {event_json}")
            if existing_event_essentials is not None:
                if misp_event_uuid := existing_event_essentials.get("misp_event_uuid"):
                    event.uuid = misp_event_uuid
                    # TODO: I can't neglect the dict, in case of a failure, the method retuns a dict anyway, try catch is not helping
                    updated_event: MISPEvent = misp.update_event(
                        event, event_id=existing_event_essentials.get("misp_event_id"), pythonify=True
                    )  # type: ignore
                    return updated_event.id
                logger.error(f"MISP event update is not possible without all event essintials - ID and UUID {existing_event_essentials=}")
                return None

            self.add_event_attributes(story, event)
            # TODO I likely can't neglect the dict, in case of a failure, the method retunrs a dict anyway
            created_event: MISPEvent = misp.add_event(event, pythonify=True)  # type: ignore
            logger.info(f"Event created in MISP with ID: {created_event.id}")
            return created_event.id
        except exceptions.PyMISPError as e:
            logger.error(f"PyMISP exception occurred, but can be misleading (e.g., if received an HTTP/301 response): {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")

    def misp_sender(self, story: dict, existing_event_essentials: dict | None = None) -> None:
        event = self.create_misp_event(story)
        if event_id := self.send_event_to_misp(event, existing_event_essentials, story):
            self.core_api.api_put(
                f"/bots/story/{story.get("id", "")}",
                {"attributes": [{"key": "misp_event_id", "value": f"{event_id}"}, {"key": "misp_event_uuid", "value": f"{event.uuid}"}]},
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
