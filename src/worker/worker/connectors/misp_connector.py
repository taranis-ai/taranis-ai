from datetime import datetime

from pymisp import ExpandedPyMISP, MISPEvent
from worker.core_api import CoreApi
from worker.log import logger


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

    def parse_parameters(self, parameters: dict):
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.misp_verifycert = parameters.get("MISP_VERIFYCERT", False)
        self.proxies = parameters.get("PROXIES", "")
        self.headers = parameters.get("HEARERS", "")

        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def send(self, connector_config: dict, stories: list):
        logger.debug(f"{connector_config=}")
        self.parse_parameters(connector_config.get("parameters", ""))
        self.misp_sender(stories)

        logger.info(f"Sending story to MISP connecector {connector_config.get('id')}")

    def create_misp_data(self, stories: list) -> list[dict]:
        event_json_list = []
        for story in stories:
            logger.debug(f"{story=}")
            misp_event = {
                "info": story.get("title"),
                "tags": story.get("tags", []),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "published": False,
                "analysis": "0",
                "threat_level_id": "1",
                "Attribute": [],
            }

            for news_item in story.get("news_items", []):
                attribute = {
                    "category": "External analysis",
                    "type": "text",
                    "value": news_item.get("title"),
                    "to_ids": False,
                    "timestamp": int(datetime.now().timestamp()),
                    "comment": f"News Title: {news_item['title']}",
                    "distribution": "0",
                    "disable_correlation": True,
                    "sharing_group_id": "1",
                    "uuid": news_item["hash"],
                }
                misp_event["Attribute"].append(attribute)
            event_json_list.append(misp_event)
        return event_json_list

    def create_misp_event(self, misp, misp_event: dict):
        event = MISPEvent()
        event.from_dict(**misp_event)
        return misp.add_event(event)

    def misp_sender(self, stories: list):
        misp_events_data = self.create_misp_data(stories)
        misp = ExpandedPyMISP(self.url, self.api_key, self.misp_verifycert)
        for misp_event in misp_events_data:
            self.create_misp_event(misp, misp_event)
        logger.info("Sending story to MISP")

    def receive(self, connector_id: str):
        logger.info(f"Receiving story from MISP connector {connector_id}")


def main():
    connector = MispConnector()
    connector_config = connector_config = {
        "description": "",
        "icon": None,
        "id": "b583f4ae-7ec3-492a-a36d-ed9cfc0b4a28",
        "last_attempted": None,
        "last_collected": None,
        "last_error_message": None,
        "name": "https",
        "parameters": {
            "ADDITIONAL_HEADERS": "",
            "API_KEY": "0QncrYi7FfCleEWzfGPOcmSTBpcBwK7gf2w8cLb3",
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


if __name__ == "__main__":
    main()
