import worker.collectors
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError

core_api = CoreApi()

collectors = {
    "rss_collector": worker.collectors.RSSCollector(),
}


def collect_by_source_id(source_id: str):
    err = None

    try:
        source = core_api.get_osint_source(source_id)
    except ConnectionError as e:
        logger.critical(e)
        return str(e)

    if not source:
        logger.error(f"Source with id {source_id} not found")
        return f"Source with id {source_id} not found"

    collector_type = source.get("collector_type")
    if not collector_type:
        logger.error(f"Source {source_id} has no collector_type")
        return f"Source {source_id} has no collector_type"

    collector = collectors.get(collector_type)
    if not collector:
        return f"Collector {collector_type} not implemented"

    if err := collector.collect(source):
        if err == "Last-Modified < Last-Attempted":
            return "Skipping source"
        core_api.update_osintsource_status(source_id, {"error": err})
        return err

    return None
