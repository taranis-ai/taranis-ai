from prefect import flow

import worker.collectors
from worker.collectors.base_collector import BaseCollector
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError


class Collector:
    def __init__(self):
        self.core_api = CoreApi()
        self.collectors = {
            "rss_collector": worker.collectors.RSSCollector(),
            "simple_web_collector": worker.collectors.SimpleWebCollector(),
            "rt_collector": worker.collectors.RTCollector(),
            "misp_collector": worker.collectors.MISPCollector(),
        }

    def get_source(self, osint_source_id: str) -> tuple[dict[str, str] | None, str | None]:
        try:
            source = self.core_api.get_osint_source(osint_source_id)
        except ConnectionError as e:
            logger.critical(e)
            return None, str(e)

        if not source:
            logger.error(f"Source with id {osint_source_id} not found")
            return None, f"Source with id {osint_source_id} not found"
        return source, None

    def get_collector(self, source: dict[str, str]) -> tuple[BaseCollector | None, str | None]:
        collector_type = source.get("type")
        if not collector_type:
            logger.error(f"Source {source['id']} has no collector_type")
            return None, f"Source {source['id']} has no collector_type"

        if collector := self.collectors.get(collector_type):
            return collector, None

        return None, f"Collector {collector_type} not implemented"

    def collect_by_source_id(self, osint_source_id: str, manual: bool = False):
        err = None

        source, err = self.get_source(osint_source_id)
        if err or not source:
            return err

        collector, err = self.get_collector(source)
        if err or not collector:
            return err

        if err := collector.collect(source, manual):
            if err == "Not modified":
                return "Not modified"
            self.core_api.update_osintsource_status(osint_source_id, {"error": err})
            return err

        return None


@flow(name="collector_task")
def collector_task(osint_source_id: str, manual: bool = False):
    collector = Collector()
    if err := collector.collect_by_source_id(osint_source_id, manual):
        return err
    return f"Successfully collected source {osint_source_id}"


@flow(name="collector_preview")
def collector_preview(osint_source_id: str):
    collector = Collector()
    source, err = collector.get_source(osint_source_id)
    if err or not source:
        return err

    collector, err = collector.get_collector(source)
    if err or not collector:
        return err

    result = collector.preview_collector(source)
    logger.debug(result)
    return result
