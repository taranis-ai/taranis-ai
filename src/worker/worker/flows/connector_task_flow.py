from prefect import flow, task
from core.log import logger
from models.connector import ConnectorTaskRequest
from core.model.connector import Connector
from core.model.news_item import NewsItem
from worker.connectors.registry import CONNECTOR_REGISTRY
from typing import List, Optional


@task
def fetch_connector_info(connector_id: str):
    logger.info(f"[connector_task] Fetching connector {connector_id}")

    connector = Connector.get(connector_id)
    if not connector:
        raise ValueError(f"Connector {connector_id} not found")

    return connector


@task
def fetch_stories_for_push(story_ids: Optional[List[str]] = None):
    logger.info(f"[connector_task] Fetching stories for push")

    if story_ids:
        stories = []
        for story_id in story_ids:
            story = NewsItem.get(story_id)
            if story:
                stories.append(story)
        logger.info(f"[connector_task] Found {len(stories)} specific stories")
    else:
        stories = NewsItem.get_unpushed()
        logger.info(f"[connector_task] Found {len(stories)} unpushed stories")

    return stories


@task
def transform_stories_for_connector(stories: List[NewsItem], connector: Connector):
    logger.info(f"[connector_task] Transforming {len(stories)} stories for connector {connector.id}")

    transformed_stories = []

    for story in stories:
        if connector.transform_config:
            transformed_story = connector.apply_transformation(story)
        else:
            transformed_story = {
                "id": story.id,
                "title": story.title,
                "content": story.content,
                "source": story.source,
                "published_date": story.published_date.isoformat() if story.published_date else None,
                "web_url": story.web_url,
                "attributes": story.attributes,
            }

        transformed_stories.append(transformed_story)

    return transformed_stories


@task
def push_to_connector(connector: Connector, transformed_stories: List[dict]):
    logger.info(f"[connector_task] Pushing {len(transformed_stories)} stories to connector {connector.id}")

    connector_class = CONNECTOR_REGISTRY.get(connector.type)
    if not connector_class:
        raise ValueError(f"Unsupported connector type: {connector.type}")

    connector_instance = connector_class(connector)

    batch_size = connector.batch_size or 100
    results = []

    for i in range(0, len(transformed_stories), batch_size):
        batch = transformed_stories[i : i + batch_size]
        result = connector_instance.push(batch)
        results.append(result)

    logger.info(f"[connector_task] Successfully pushed stories to connector {connector.id}")
    return results


@task
def update_story_status(stories: List[NewsItem], connector: Connector, results: List):
    logger.info(f"[connector_task] Updating status for {len(stories)} stories")

    for story in stories:
        story.mark_pushed_to_connector(connector.id)

    return len(stories)


@flow(name="connector-task-flow")
def connector_task_flow(request: ConnectorTaskRequest):
    """Main flow for pushing data to connectors"""
    try:
        logger.info(f"[connector_task_flow] Starting push to connector {request.connector_id}")

        connector = fetch_connector_info(request.connector_id)
        stories = fetch_stories_for_push(request.story_ids)

        if not stories:
            logger.info(f"[connector_task_flow] No stories to push to connector {request.connector_id}")
            return {"message": f"No stories to push to connector {request.connector_id}", "count": 0}

        transformed_stories = transform_stories_for_connector(stories, connector)
        results = push_to_connector(connector, transformed_stories)
        count = update_story_status(stories, connector, results)

        logger.info(f"[connector_task_flow] Successfully pushed {count} stories to connector {request.connector_id}")
        return {
            "message": f"Connector with id: {request.connector_id} scheduled",
            "count": count,
            "results": results,
        }

    except Exception as e:
        logger.exception(f"[connector_task_flow] Failed to push to connector {request.connector_id}")
        return {
            "error": "Could not reach rabbitmq",
            "details": str(e),
        }
