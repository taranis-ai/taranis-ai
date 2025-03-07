import json
import urllib3
from pymisp import ExpandedPyMISP, MISPEvent

from .base_publisher import BasePublisher
from worker.types import Product


class MISPPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "MISP_PUBLISHER"
        self.name = "MISP Publisher"
        self.description = "Publisher for publishing in MISP"

    def publish(self, publisher: dict, product: dict, rendered_product: Product):
        parameters = publisher.get("parameters")

        misp_url = parameters.get("MISP_URL")
        misp_key = parameters.get("MISP_API_KEY")
        misp_verifycert = False

        event_json = json.loads(rendered_product.data.decode("utf-8"))

        urllib3.disable_warnings()

        misp = ExpandedPyMISP(misp_url, misp_key, misp_verifycert)

        event = MISPEvent()
        event.load(event_json)
        return misp.add_event(event)
