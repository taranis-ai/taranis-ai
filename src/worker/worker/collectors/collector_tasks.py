from prefect import flow
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


@flow(name="collector_task")
def collector_task(osint_source_id: str, manual: bool = False):
    collector = Collector()
    try:
        source = collector.get_source(osint_source_id)
        col = collector.get_collector(source)
        formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{col.name}")
        logger.info(f"Starting collection for source '{source.get('name')}' (ID: {osint_source_id})")
        with collector_log_fmt(logger, formatter):
            col.collect(source, manual)
        collector.core_api.run_post_collection_bots(osint_source_id)
        return f"Successfully collected source {osint_source_id}"
    except NoChangeError as e:
        logger.info(f"No change for source {osint_source_id}: {str(e)}")
        return str(e)
    except Exception as e:
        logger.exception(f"Failed to collect source {osint_source_id}")
        return {"error": str(e)}


@flow(name="collector_preview")
def collector_preview(osint_source_id: str):
    collector = Collector()
    try:
        source = collector.get_source(osint_source_id)
        col = collector.get_collector(source)
        formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{col.name}")
        logger.info(f"Starting preview for source '{source.get('name')}' (ID: {osint_source_id})")
        with collector_log_fmt(logger, formatter):
            return col.preview_collector(source)
    except Exception as e:
        logger.exception(f"Failed to preview source {osint_source_id}")
        return {"error": str(e)}
