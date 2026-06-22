"""RQ Connector Tasks

Functions for pushing stories to external systems (MISP, etc.).
"""

import json
import re
from typing import Any

from rq import get_current_job

from worker.connectors import MispConnector
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.log import logger


def connector_task(connector_id: str, story_ids: list[str] | None) -> dict[str, Any]:
    """Push stories to an external connector system.

    Args:
        connector_id: ID of the connector configuration
        story_ids: List of story IDs to send

    Returns:
        Connector execution result payload

    Raises:
        RuntimeError: If connector not found or execution fails
    """
    job = get_current_job()
    core_api = CoreApi()

    logger.info(f"Running connector with id: {connector_id}, job id: {job.id if job else 'manual'}")

    # Get connector configuration and implementation
    try:
        connector_config: dict = _get_connector_config(core_api, connector_id)
        connector = _get_connector(connector_config.get("type", ""))
    except Exception as e:
        if job:
            connector_type = connector_config.get("type", "connector_task") if "connector_config" in locals() else "connector_task"
            reason = "connector_not_found" if "not found" in str(e).lower() else "connector_not_implemented"
            core_api.save_task_result(
                job.id,
                "connector_task",
                "FAILURE",
                worker_id=connector_id,
                worker_type=connector_type,
                result=build_failure_task_result(
                    str(e),
                    reason=reason,
                    data={"connector_id": connector_id, "story_ids": story_ids},
                ),
            )
        logger.exception(f"Failed to get connector with id: {connector_id}")
        raise RuntimeError(f"Failed to get connector with id: {connector_id}") from e

    # Get connector data (stories)
    try:
        connector_data = _get_connector_data(core_api, connector_id, connector_config, story_ids)
    except Exception as e:
        if job:
            core_api.save_task_result(
                job.id,
                "connector_task",
                "FAILURE",
                worker_id=connector_id,
                worker_type=connector_config.get("type", "connector_task"),
                result=build_failure_task_result(
                    str(e),
                    reason="connector_data_load_failed",
                    data={"connector_id": connector_id, "story_ids": story_ids},
                ),
            )
        raise

    # Execute connector
    try:
        connector_result = connector.execute(connector_data)
        if not isinstance(connector_result, dict):
            raise RuntimeError(f"Connector {connector.type} returned an invalid result payload")

        logger.info(f"Connector with id: {connector_id} executed successfully")
        result = {
            "connector_id": connector_id,
            "connector_type": connector.type,
            "action": connector_result.get("action", "mixed"),
            "message": connector_result.get("message", "Connector executed successfully"),
            "sync_results": connector_result.get("sync_results", []),
            "story_ids": story_ids,
        }
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
        logger.exception(f"Error executing connector with id: {connector_id}")
        if job:
            core_api.save_task_result(
                job.id,
                "connector_task",
                "FAILURE",
                worker_id=connector_id,
                worker_type=connector_config.get("type", "connector_task"),
                result=build_failure_task_result(
                    f"Error executing connector with id: {connector_id}",
                    reason="connector_execution_failed",
                    data={"connector_id": connector_id, "story_ids": story_ids},
                ),
            )
        raise RuntimeError(f"Error executing connector with id: {connector_id}") from e


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
        RuntimeError: If connector not found or has no type
    """
    connector_config = core_api.get_connector_config(connector_id)
    if not connector_config:
        raise RuntimeError(f"Connector with id {connector_id} not found")

    connector_type = connector_config.get("type")
    if connector_type is None:
        raise RuntimeError(f"Connector type for id {connector_id} not found")

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
    raise RuntimeError(f"Connector type '{connector_type}' not implemented")


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
        RuntimeError: If stories not found
    """
    connector_data: dict[str, Any] = {"connector_config": connector_config}
    normalized_story_ids = story_ids or []
    logger.info(f"Sending story {normalized_story_ids} to connector {connector_id}")

    try:
        connector_data["story"] = get_story_by_id(core_api, normalized_story_ids)
    except Exception as e:
        logger.exception(f"Failed to get stories with id: {normalized_story_ids}")
        raise RuntimeError(f"Failed to get stories with id: {normalized_story_ids}") from e

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
