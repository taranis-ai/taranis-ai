from prefect import flow, task
from worker.log import logger
from models.prefect import CollectorTaskRequest
from worker.collectors.registry import COLLECTOR_REGISTRY


@task
def fetch_osint_source_info(source_id: str):
    """Fetch OSINT source configuration"""
    logger.info(f"[collector_task] Fetching OSINT source {source_id}")

    try:
        # Use CoreApi to fetch source
        from worker.core_api import CoreApi

        core_api = CoreApi()

        if source := core_api.get_osint_source(source_id):
            return source
        else:
            raise ValueError(f"Source with id {source_id} not found")

    except Exception as e:
        logger.error(f"Failed to fetch OSINT source: {e}")
        raise


@task
def validate_source_config(source: dict):
    """Validate source has required collector type"""
    logger.info("[collector_task] Validating source configuration")

    if not source.get("type"):
        raise ValueError(f"Source {source.get('id')} has no collector_type")

    return source


@task
def execute_collector(source: dict, manual: bool = False):
    """Execute the collector for the given source"""
    logger.info(f"[collector_task] Executing collector for source '{source.get('name')}'")

    collector_type = source.get("type")
    collector_class = COLLECTOR_REGISTRY.get(collector_type)

    if not collector_class:
        raise ValueError(f"Collector of type {collector_type} not implemented")

    try:
        collector_instance = collector_class()

        task_description = f"Collect: source '{source.get('name')}' with id {source.get('id')} using collector: '{collector_instance.name}'"

        logger.info(f"Starting collector task: {task_description}")

        # Execute the collector
        result = collector_instance.collect(source, manual)

        if result is None:
            result = f"Collection completed for source '{source.get('name')}'"

        logger.info("[collector_task] Collector execution completed successfully")
        return result

    except Exception as e:
        if str(e) == "Not modified":
            logger.info(f"[collector_task] Source '{source.get('name')}' was not modified")
            return f"Source '{source.get('name')}' with id {source.get('id')} was not modified"
        else:
            logger.error(f"Collector execution failed: {e}")
            raise


@flow(name="collector-task-flow")
def collector_task_flow(request: CollectorTaskRequest):
    """Main collector task flow for gathering data from sources"""
    try:
        logger.info(f"[collector_task_flow] Starting collection from source {request.source_id}")

        # Fetch source configuration
        source = fetch_osint_source_info(request.source_id)

        # Validate source configuration
        validated_source = validate_source_config(source)

        # Execute collector
        result = execute_collector(validated_source, request.preview)

        logger.info(f"[collector_task_flow] Successfully completed collection from source {request.source_id}")
        return {"message": f"Collection from source {request.source_id} completed", "result": result, "status": "success"}

    except Exception as e:
        logger.exception(f"[collector_task_flow] Failed to collect from source {request.source_id}")
        return {"error": "Could not reach rabbitmq", "details": str(e), "status": "failed"}
