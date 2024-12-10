from celery import Task

from worker.connectors import MispConnector
from worker.log import logger
from worker.core_api import CoreApi


class ConnectorTask(Task):
    name = "connector_task"
    max_retries = 3
    priority = 5
    default_retry_delay = 60
    time_limit = 300
    ignore_result = True

    def __init__(self):
        self.core_api = CoreApi()
        self.connectors = {
            "misp_connector": MispConnector(),
        }

    def get_connector(self, connector_id: str) -> MispConnector | None:
        connector_config = self.core_api.get_connector_config(connector_id)

        if not connector_config:
            logger.error(f"Connector with id {connector_id} not found")
            raise RuntimeError(f"Connector with id {connector_id} not found")
        if connector_type := connector_config.get("type"):
            return self.connectors.get(connector_type)
        return None

    def get_story(self, story_id: str) -> list:
        story = self.core_api.get_stories({"story_id": story_id})

        if not story:
            logger.error(f"Story with id {story_id} not found")
            raise RuntimeError(f"Story with id {story} not found")
        return story

    def run(self, connector_id: str, story_id: str | None):
        if connector := self.get_connector(connector_id):
            if story_id:
                logger.info(f"Sending story {story_id} to connector {connector_id}")
                return connector.send(connector_id)

            return connector.receive(connector_id)
        logger.info(f"Connector with id: {connector_id} was not found")
        return None
