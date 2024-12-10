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

        self.url: str
        self.api_key: str

    def send(self, connector_id: str):
        logger.info(f"Sending story to MISP {connector_id}")

    def receive(self, connector_id: str):
        logger.info(f"Receiving story from MISP {connector_id}")
