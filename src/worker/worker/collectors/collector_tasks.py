from celery import Task

import worker.collectors
from worker.collectors.base_collector import BaseCollector
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError


class CollectorTask(Task):
    name = "collector_task"
    max_retries = 3
    default_retry_delay = 60
    time_limit = 60

    def __init__(self):
        self.core_api = CoreApi()
        self.collectors = {
            "rss_collector": worker.collectors.RSSCollector(),
            "simple_web_collector": worker.collectors.SimpleWebCollector(),
        }

    def run(self, source_id: str):
        logger.info(f"Starting collector task {self.name}")
        if err := self.collect_by_source_id(source_id):
            return err
        self.core_api.run_post_collection_bots(source_id)
        return f"Succesfully collected source {source_id}"

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.info(f"Finished collector task {self.name} with status {status}")
        super().after_return(status, retval, task_id, args, kwargs, einfo)

    def get_source(self, source_id: str) -> tuple[dict[str, str] | None, str | None]:
        try:
            source = self.core_api.get_osint_source(source_id)
        except ConnectionError as e:
            logger.critical(e)
            return None, str(e)

        if not source:
            logger.error(f"Source with id {source_id} not found")
            return None, f"Source with id {source_id} not found"
        return source, None

    def get_collector(self, source: dict[str, str]) -> tuple[BaseCollector | None, str | None]:
        collector_type = source.get("type")
        if not collector_type:
            logger.error(f"Source {source['id']} has no collector_type")
            return None, f"Source {source['id']} has no collector_type"

        if collector := self.collectors.get(collector_type):
            return collector, None

        return None, f"Collector {collector_type} not implemented"

    def collect_by_source_id(self, source_id: str):
        err = None

        source, err = self.get_source(source_id)
        if err or not source:
            return err

        collector, err = self.get_collector(source)
        if err or not collector:
            return err

        if err := collector.collect(source):
            if err == "Last-Modified < Last-Attempted":
                return "Skipping source"
            self.core_api.update_osintsource_status(source_id, {"error": err})
            return err

        return None
