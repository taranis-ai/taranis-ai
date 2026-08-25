"""RQ Connector Tasks

Functions for pushing stories to external systems (MISP, etc.).
"""

import json
import re
from typing import Any

from rq import get_current_job

from worker.connectors import MispConnector
from worker.connectors.exceptions import ConnectorError
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.log import logger


def connector_task(connector_id: str, story_ids: list[str] | None, auto_update: bool = False) -> dict[str, Any]:
    """Push stories to an external connector system.

    Args:
        connector_id: ID of the connector configuration
        story_ids: List of story IDs to send

    Returns:
        Connector execution result payload

    Raises:
        ConnectorError: If connector setup, data loading, or execution fails
    """
    job = get_current_job()
    core_api = CoreApi()

    logger.info(f"Running connector with id: {connector_id}, job id: {job.id if job else 'manual'}")

    connector_config: dict[str, Any] = {}
    connector: MispConnector | None = None
    failure_message = "Connector task failed"
    try:
        connector_config = _get_connector_config(core_api, connector_id)
        connector = _get_connector(connector_config.get("type", ""))
        connector_data = _get_connector_data(core_api, connector_id, connector_config, story_ids)
        connector_result = connector.execute(connector_data, auto_update=auto_update)
        if not isinstance(connector_result, dict):
            raise TypeError(f"Connector {connector.type} returned an invalid result payload")

        result = {
            "connector_id": connector_id,
            "connector_type": connector.type,
            "action": connector_result.get("action", "mixed"),
            "message": connector_result.get("message", "Connector executed successfully"),
            "sync_results": connector_result.get("sync_results", []),
            "story_ids": story_ids,
            "auto_update": auto_update,
        }
        logger.info(f"Connector with id: {connector_id} executed successfully")
        if job:
            core_api.save_task_result(
                job.id,
                "connector_task",
                "SUCCESS",
                worker_id=connector_id,
                worker_type=connector.type,
                result=build_success_task_result(
                    default_message="Connector executed successfully",
                    output=connector_result,
                    base_data=result,
                ),
            )
        return result
    except Exception as e:
        error = e if isinstance(e, ConnectorError) else ConnectorError(failure_message, "connector_execution_failed")
        logger.error(f"{error.public_message} (reason={error.reason}, exception_type={type(e).__name__})")
        worker_type = getattr(connector, "type", None) or connector_config.get("type", "connector_task")
        if job:
            core_api.save_task_result(
                job.id,
                "connector_task",
                "FAILURE",
                worker_id=connector_id,
                worker_type=worker_type,
                result=build_failure_task_result(
                    error.public_message,
                    reason=error.reason,
                    data={"connector_id": connector_id, "story_ids": story_ids},
                ),
            )
        if isinstance(e, ConnectorError):
            raise
        raise error from e


def drop_utf16_surrogates(data: str) -> str:
    """Drop any leftover UTF-16 surrogates (U+D800–U+DFFF).

    MISP does not support surrogate pairs. This function cleans them out.

    Args:
        data: String potentially containing UTF-16 surrogates

    Returns:
        Cleaned string without surrogates
    """
    try:
        # MISP does not support surrogate pairs. The cleanest way found is to decode with "raw_unicode_escape"
        # and "backslashreplace" to drop surrogate pairs.
        decoded = data.encode("utf-8", "surrogatepass").decode("raw_unicode_escape", "backslashreplace")
    except UnicodeDecodeError:
        logger.warning("Failed to decode data with surrogatepass")
        decoded = data

    # TODO: Unfortunately, we need to drop the surrogate pairs manually
    return re.sub(r"[\uD800-\uDFFF]", "", decoded)


def _get_connector_config(core_api: CoreApi, connector_id: str) -> dict:
    """Fetch connector configuration from core API.

    Args:
        core_api: CoreApi instance
        connector_id: ID of the connector

    Returns:
        Connector configuration dictionary

    Raises:
        ConnectorError: If connector not found or has no type
    """
    connector_config = core_api.get_connector_config(connector_id)
    if not connector_config:
        raise ConnectorError("Connector not found", "connector_not_found")

    connector_type = connector_config.get("type")
    if connector_type is None:
        raise ConnectorError("Connector type is missing", "connector_type_missing")

    return connector_config


def _get_connector(connector_type: str) -> MispConnector:
    """Get connector implementation for a given type.

    Args:
        connector_type: Connector type name

    Returns:
        Connector implementation instance
    """
    connectors = {
        "misp_connector": MispConnector(),
    }
    if connector := connectors.get(connector_type):
        return connector
    raise ConnectorError("Connector type is not supported", "connector_not_implemented")


def _get_connector_data(
    core_api: CoreApi,
    connector_id: str,
    connector_config: dict[str, Any],
    story_ids: list[str] | None,
) -> dict[str, Any]:
    """Fetch and prepare data for connector execution.

    Args:
        core_api: CoreApi instance
        connector_id: ID of the connector
        connector_config: Connector configuration
        story_ids: List of story IDs to fetch

    Returns:
        Dictionary containing connector_config and stories

    Raises:
        ConnectorError: If stories cannot be loaded
    """
    connector_data: dict[str, Any] = {"connector_config": connector_config}
    normalized_story_ids = story_ids or []
    logger.info(f"Sending story {normalized_story_ids} to connector {connector_id}")

    try:
        connector_data["story"] = get_story_by_id(core_api, normalized_story_ids)
    except Exception as e:
        logger.exception(f"Failed to get stories with id: {normalized_story_ids}")
        raise ConnectorError("Could not load stories for connector", "connector_data_load_failed") from e

    return connector_data


def get_story_by_id(core_api: CoreApi, story_ids: list[str]) -> list:
    """Fetch stories by their IDs.

    Args:
        core_api: CoreApi instance
        story_ids: List of story IDs to fetch

    Returns:
        List of story dictionaries

    Raises:
        RuntimeError: If no stories found
    """
    search_queries = [{"story_id": story_id} for story_id in story_ids]
    stories = []

    for query in search_queries:
        if story := core_api.get_stories(query):
            storylist = json.dumps(story)
            storylist = drop_utf16_surrogates(storylist)
            story = json.loads(storylist)
            stories.extend(story)

    if not stories:
        logger.error(f"Stories {search_queries} not found")
        raise RuntimeError(f"Stories with queries {search_queries} not found")

    return stories
