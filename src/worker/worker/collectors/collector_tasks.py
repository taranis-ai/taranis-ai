from celery import Task
from contextlib import contextmanager

import worker.collectors
from worker.collectors.base_collector import BaseCollector, NoChangeError
from worker.log import logger, TaranisLogFormatter, TaranisLogger
from worker.core_api import CoreApi
from typing import Any


@contextmanager
def collector_log_fmt(logger: TaranisLogger, collector_formatter: TaranisLogFormatter):
    stream_handler = logger.get_stream_handler()
    if stream_handler is None:
        yield
        return

    old_fmt = stream_handler.formatter
    stream_handler.setFormatter(collector_formatter)
    try:
        yield
    finally:
        stream_handler.setFormatter(old_fmt)


class Collector:
    def __init__(self):
        self.core_api = CoreApi()
        self.collectors = {
            "rss_collector": worker.collectors.RSSCollector(),
            "simple_web_collector": worker.collectors.SimpleWebCollector(),
            "rt_collector": worker.collectors.RTCollector(),
            "misp_collector": worker.collectors.MISPCollector(),
            "ppn_collector": worker.collectors.PPNCollector(),
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

    def run(self, osint_source_id: str, manual: bool = False):
        self.collector = Collector()
        source = self.collector.get_source(osint_source_id)
        collector = self.collector.get_collector(source)
        formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector.name} {self.request.id}")
        task_description = (
            f"Collect: source '{source.get('name')}' with id {source.get('id')} using collector: '{collector.name}' with id {self.request.id}"
        )
        self.request.task_description = task_description

        logger.info(f"Starting collector task: {task_description}")
        with collector_log_fmt(logger, formatter):
            try:
                collection_result = collector.collect(source, manual)
            except NoChangeError as e:
                self.update_state(state="NOT_MODIFIED")
                return f"'{source.get('name')}': {str(e)}"
            except Exception as e:
                raise RuntimeError(e) from e

        self.core_api.run_post_collection_bots(osint_source_id)
        return f"'{source.get('name')}': {collection_result}"

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Collector task with id: {task_id} failed.\nDescription: {self.request.task_description}")


class CollectorPreview(Task):
    name = "collector_preview"
    track_started = True
    acks_late = True
    priority = 8

    def run(self, osint_source_id: str):
        collector = Collector()
        source = collector.get_source(osint_source_id)
        collector = collector.get_collector(source)
        formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector.name} {self.request.id}")
        task_description = (
            f"Preview: source '{source.get('name')}' with id {source.get('id')} using collector: '{collector.name}' with id {self.request.id}"
        )
        logger.info(f"Starting collector task: {task_description}")
        with collector_log_fmt(logger, formatter):
            try:
                preview_result = collector.preview_collector(source)
            except NoChangeError as e:
                self.update_state(state="NOT_MODIFIED")
                return f"'{source.get('name')}': {str(e)}"
            except Exception as e:
                raise RuntimeError(e) from e
        return preview_result

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Collector task with id: {task_id} failed.\nDescription: {kwargs.get('task_description', '')}")
