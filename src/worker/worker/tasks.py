from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi
from worker.collectors.rss_collector import RSSCollector

@shared_task
def collect(source_id: str):
    core_api = CoreApi()
    source = core_api.get_osint_source(source_id)
    if not source:
        logger.error(f"Source with id {source_id} not found")
        return

    if source["type"] == "RSS_COLLECTOR":
        return RSSCollector().collect(source)
    return "Not implemented"

@shared_task
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"
