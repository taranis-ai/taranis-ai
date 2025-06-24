from celery import Task

import worker.collectors
from worker.collectors.base_collector import BaseCollector
from worker.log import logger
from worker.core_api import CoreApi
from typing import Any


class Collector:
    def __init__(self):
        self.core_api = CoreApi()
        self.collectors = {
            "rss_collector": worker.collectors.RSSCollector(),
            "simple_web_collector": worker.collectors.SimpleWebCollector(),
            "rt_collector": worker.collectors.RTCollector(),
            "misp_collector": worker.collectors.MISPCollector(),
        }

    def get_source(self, osint_source_id: str) -> dict[str, Any]:
        if source := self.core_api.get_osint_source(osint_source_id):
            return source
        raise ValueError(f"Source with id {osint_source_id} not found")

    def get_collector(self, source: dict[str, Any]) -> BaseCollector:
        if collector_type := source.get("type"):
            if collector := self.collectors.get(collector_type):
                return collector
            raise ValueError(f"Collector of type {collector_type} not implemented")
        raise ValueError(f"Source {source['id']} has no collector_type")


class CollectorTask(Task):
    name = "collector_task"
    max_retries = 3
    priority = 5
    default_retry_delay = 60
    time_limit = 300

    def __init__(self):
        self.core_api = CoreApi()

    def run(self, osint_source_id: str, manual: bool = False, **kwargs):
        self.collector = Collector()
        source = self.collector.get_source(osint_source_id)
        collector = self.collector.get_collector(source)
        task_description = f"Collect source '{source.get('name')}' with id {source.get('id')} using collector: '{collector.name}'"
        kwargs["task_description"] = task_description

        logger.info(f"Starting collector task: {task_description}")
        try:
            collector.collect(source, manual)
        except Exception as e:
            if e == "Not modified":
                return f"Source '{source.get('name')}' with id {osint_source_id} was not modified"
            self.core_api.update_osintsource_status(osint_source_id, {"error": e})

        self.core_api.run_post_collection_bots(osint_source_id)
        return f"Successfully collected source '{source.get('name')}' with id {osint_source_id}"

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Collector task with id: {task_id} failed.\nDescription: {kwargs.get('task_description', '')}\nException: {exc}")


class CollectorPreview(Task):
    name = "collector_preview"
    track_started = True
    acks_late = True
    priority = 8

    def run(self, osint_source_id: str, **kwargs):
        collector = Collector()
        source = collector.get_source(osint_source_id)
        collector = collector.get_collector(source)

        return collector.preview_collector(source)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Collector task with id: {task_id} failed.\nDescription: {kwargs.get('task_description', '')}\nException: {exc}")
