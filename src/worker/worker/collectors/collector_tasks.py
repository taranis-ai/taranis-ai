import worker.collectors
from worker.collectors.base_collector import BaseCollector
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError

core_api = CoreApi()

collectors = {
    "rss_collector": worker.collectors.RSSCollector(),
    "simple_web_collector": worker.collectors.SimpleWebCollector(),
}


def get_source(source_id: str) -> tuple[dict[str, str] | None, str | None]:
    try:
        source = core_api.get_osint_source(source_id)
    except ConnectionError as e:
        logger.critical(e)
        return None, str(e)

    if not source:
        logger.error(f"Source with id {source_id} not found")
        return None, f"Source with id {source_id} not found"
    return source, None


def get_collector(source: dict[str, str]) -> tuple[BaseCollector | None, str | None]:
    collector_type = source.get("type")
    if not collector_type:
        logger.error(f"Source {source['id']} has no collector_type")
        return None, f"Source {source['id']} has no collector_type"

    if collector := collectors.get(collector_type):
        return collector, None

    return None, f"Collector {collector_type} not implemented"


def collect_by_source_id(source_id: str):
    err = None

    source, err = get_source(source_id)
    if err or not source:
        return err

    collector, err = get_collector(source)
    if err or not collector:
        return err

    if err := collector.collect(source):
        if err == "Last-Modified < Last-Attempted":
            return "Skipping source"
        core_api.update_osintsource_status(source_id, {"error": err})
        return err

    return None
