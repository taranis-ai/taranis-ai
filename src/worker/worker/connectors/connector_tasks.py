import re
from celery import Task
import json
from typing import Any

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

    def drop_utf16_surrogates(self, data: str) -> str:
        """
        Drop any leftover UTF-16 surrogates (U+D800–U+DFFF).
        (But leave \\n, \\t, \\", etc. intact.)
        """
        try:
            # MISP does not support surrogate pairs. The cleanest way found is to decode with "raw_unicode_escape"
            # and "backslashreplace" to drop surrogate pairs.
            decoded = data.encode("utf-8", "surrogatepass").decode("raw_unicode_escape", "backslashreplace")
        except UnicodeDecodeError:
            logger.warning("Failed to decode data with surrogatepass")
            decoded = data

        # TODO: Unfrotunately, we need to drop the surrogate pairs manually
        return re.sub(r"[\uD800-\uDFFF]", "", decoded)

    def get_connector_config(self, connector_id: str) -> dict:
        connector_config = self.core_api.get_connector_config(connector_id)
        if not connector_config:
            raise RuntimeError(f"Connector with id {connector_id} not found")

        connector_type = connector_config.get("type")
        if connector_type is None:
            raise RuntimeError(f"Connector type for id {connector_id} not found")

        return connector_config

    def get_connector(self, connector_type: str) -> MispConnector | None:
        return self.connectors.get(connector_type)

    def get_connector_data(self, connector_id: str, connector_config: dict[str, Any], story_ids: list[str]) -> dict[str, Any]:
        connector_data: dict[str, Any] = {"connector_config": connector_config}
        logger.info(f"Sending story {story_ids} to connector {connector_id}")
        try:
            connector_data["story"] = self.get_story_by_id(story_ids)
        except Exception as e:
            logger.exception(f"Failed to get stories with id: {story_ids}")
            raise RuntimeError(f"Failed to get stories with id: {story_ids}") from e

        return connector_data

    def get_story_by_id(self, story_ids: list[str]) -> list:
        search_queries = [{"story_id": story_id} for story_id in story_ids]
        stories = []
        for query in search_queries:
            if story := self.core_api.get_stories(query):
                storylist = json.dumps(story)
                storylist = self.drop_utf16_surrogates(storylist)
                story = json.loads(storylist)
                stories.extend(story)
        if not stories:
            logger.error(f"Stories {query} not found")
            raise RuntimeError(f"Story with id {query} not found")
        return stories

    def run(self, connector_id: str, story_ids: list[str]) -> None:
        logger.info(f"Running connector with id: {connector_id}")
        connector = None
        try:
            connector_config: dict = self.get_connector_config(connector_id)
            connector: MispConnector | None = self.get_connector(connector_config.get("type", ""))
        except Exception as e:
            logger.exception(f"Failed to get connector with id: {connector_id}")
            raise RuntimeError(f"Failed to get connector with id: {connector_id}") from e

        connector_data = self.get_connector_data(connector_id, connector_config, story_ids)

        try:
            if connector is not None:
                connector.execute(connector_data)
        except Exception as e:
            logger.exception(f"Error executing connector with id: {connector_id}")
            raise RuntimeError(f"Error executing connector with id: {connector_id}") from e
        logger.info(f"Connector with id: {connector_id} was not found")
        return None
