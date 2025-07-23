from prefect import flow, task
import re
import json
from core.log import logger
from models.models.connector import ConnectorTaskRequest
from worker.core_api import CoreApi
import worker.connectors  


@task
def drop_utf16_surrogates(data: str) -> str:
    """
    Drop any leftover UTF-16 surrogates (U+D800–U+DFFF).
    """
    try:
        # MISP does not support surrogate pairs. The cleanest way found is to decode with "raw_unicode_escape"
        # and "backslashreplace" to drop surrogate pairs.
        decoded = data.encode("utf-8", "surrogatepass").decode("raw_unicode_escape", "backslashreplace")
    except UnicodeDecodeError:
        logger.warning("Failed to decode data with surrogatepass")
        decoded = data

    # TODO:  we need to drop the surrogate pairs manually
    return re.sub(r"[\uD800-\uDFFF]", "", decoded)


@task
def get_connector_config(connector_id: str):
    """Get connector configuration from CoreApi"""
    logger.info(f"[connector_task] Getting connector config for {connector_id}")
    
    core_api = CoreApi()
    connector_config = core_api.get_connector_config(connector_id)
    
    if not connector_config:
        raise RuntimeError(f"Connector with id {connector_id} not found")
    
    connector_type = connector_config.get("type")
    if connector_type is None:
        raise RuntimeError(f"Connector type for id {connector_id} not found")
    
    return connector_config, connector_type


@task
def get_connector_instance(connector_type: str):
    """Get connector instance from registry"""
    logger.info(f"[connector_task] Getting connector instance for type {connector_type}")
    
    connectors = {
        "misp_connector": worker.connectors.MISPConnector(),
    }
    
    connector = connectors.get(connector_type)
    if not connector:
        raise RuntimeError(f"Connector type {connector_type} not implemented")
    
    return connector


@task
def get_stories_by_id(story_ids: list[str]):
    """
    Get stories by ID list 
    Includes UTF-16 surrogate cleaning 
    """
    logger.info(f"[connector_task] Getting stories for IDs: {story_ids}")
    
    core_api = CoreApi()
    search_queries = [{"story_id": story_id} for story_id in story_ids]
    stories = []
    
    for query in search_queries:
        if story := core_api.get_stories(query):
            # Apply UTF-16 surrogate cleaning 
            story_json = json.dumps(story)
            cleaned_story_json = drop_utf16_surrogates(story_json)
            cleaned_story = json.loads(cleaned_story_json)
            stories.extend(cleaned_story)
    
    if not stories:
        logger.error(f"Stories {story_ids} not found")
        raise RuntimeError(f"Story with id {story_ids} not found")
    
    return stories


@task
def execute_connector(connector, connector_config: dict, stories: list):
    """Execute connector with config and stories"""
    logger.info(f"[connector_task] Executing connector with {len(stories)} stories")
    
    try:
        return connector.execute(connector_config, stories)
    except Exception as e:
        connector_id = connector_config.get("id", "unknown")
        logger.exception(f"Error executing connector with id: {connector_id}")
        raise RuntimeError(f"Error executing connector with id: {connector_id}") from e


@flow(name="connector-task-flow")
def connector_task_flow(request: ConnectorTaskRequest):

    try:
        logger.info(f"[connector_task_flow] Starting connector task - matches Celery behavior")
        
        # Get connector config and type 
        try:
            connector_config, connector_type = get_connector_config(request.connector_id)
        except Exception as e:
            logger.exception(f"Failed to get connector with id: {request.connector_id}")
            raise RuntimeError(f"Failed to get connector with id: {request.connector_id}") from e
        
        # Get connector instance from registry 
        connector = get_connector_instance(connector_type)
        
        if connector:
            logger.info(f"Sending story {request.story_ids} to connector {request.connector_id}")
            
            # Get stories by ID with UTF-16 cleaning 
            try:
                stories = get_stories_by_id(request.story_ids)
            except Exception as e:
                logger.exception(f"Failed to get stories with id: {request.story_ids}")
                raise RuntimeError(f"Failed to get stories with id: {request.story_ids}") from e
            
            # Execute connector 
            if connector_config is not None:
                result = execute_connector(connector, connector_config, stories)
                logger.info(f"[connector_task_flow] Connector task completed successfully")
                return result
            else:
                raise RuntimeError(f"Connector config for id {request.connector_id} is None")
        
        logger.info(f"Connector with id: {request.connector_id} was not found")
        return None
        
    except Exception as e:
        logger.exception(f"[connector_task_flow] Connector task failed")
        raise