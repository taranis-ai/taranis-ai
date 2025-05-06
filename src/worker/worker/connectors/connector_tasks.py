import re
from celery import Task
import json

from worker.connectors import MISPConnector
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
            "misp_connector": MISPConnector(),
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

    def get_connector(self, connector_id: str) -> tuple[MISPConnector | None, dict | None]:
        connector_config = self.core_api.get_connector_config(connector_id)
        if not connector_config:
            raise RuntimeError(f"Connector with id {connector_id} not found")

        connector_type = connector_config.get("type")
        if connector_type is None:
            raise RuntimeError(f"Connector type for id {connector_id} not found")
        return self.connectors.get(connector_type), connector_config

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

    def run(self, connector_id: str, story_id: list):
        try:
            connector, connector_config = self.get_connector(connector_id)
        except Exception as e:
            logger.exception(f"Failed to get connector with id: {connector_id}")
            raise RuntimeError(f"Failed to get connector with id: {connector_id}") from e

        if connector:
            logger.info(f"Sending story {story_id} to connector {connector_id}")
            try:
                stories = self.get_story_by_id(story_id)
            except Exception as e:
                logger.exception(f"Failed to get stories with id: {story_id}")
                raise RuntimeError(f"Failed to get stories with id: {story_id}") from e

            if connector_config is not None:
                try:
                    return connector.execute(connector_config, stories)
                except Exception as e:
                    logger.exception(f"Error executing connector with id: {connector_id}")
                    raise RuntimeError(f"Error executing connector with id: {connector_id}") from e
            else:
                raise RuntimeError(f"Connector config for id {connector_id} is None")

        logger.info(f"Connector with id: {connector_id} was not found")
        return None
