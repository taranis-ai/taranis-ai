"""RQ Collector Tasks

Functions for collecting news from OSINT sources.
"""

from contextlib import contextmanager
from rq import get_current_job
from typing import Any

import worker.collectors
from worker.collectors.base_collector import BaseCollector, NoChangeError
from worker.core_api import CoreApi
from worker.log import TaranisLogFormatter, TaranisLogger, logger


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
            "misp_collector": worker.collectors.MispCollector(),
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


def collector_task(osint_source_id: str, manual: bool = False):
    """Collect news from an OSINT source.

    Args:
        osint_source_id: ID of the OSINT source to collect from
        manual: Whether this is a manual collection (not scheduled)

    Returns:
        str: Collection result message

    Raises:
        ValueError: If source or collector not found
        RuntimeError: If collection fails
    """
    job = get_current_job()
    core_api = CoreApi()
    collector = Collector()

    source = collector.get_source(osint_source_id)
    collector_impl = collector.get_collector(source)
    formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector_impl.name} {job.id if job else 'preview'}")
    task_description = (
        f"Collect: source '{source.get('name')}' with id {source.get('id')} using collector: '{collector_impl.name}' "
        f"with job id {job.id if job else 'preview'}"
    )

    result_message = None
    task_status = "SUCCESS"

    logger.info(f"Starting collector task: {task_description}")
    with collector_log_fmt(logger, formatter):
        try:
            collection_result = collector_impl.collect(source, manual)
            result_message = f"'{source.get('name')}': {collection_result}"
        except NoChangeError as e:
            logger.info(f"No changes detected: {e}")
            result_message = f"No changes: {e}"
            if job:
                job.meta["status"] = "NOT_MODIFIED"
                job.meta["message"] = str(e)
                job.save_meta()

            # Save task result to database
            if job:
                _save_task_result(job.id, "collector_task", result_message, task_status, core_api)

            return result_message
        except Exception as e:
            logger.error(f"Collector task failed: {task_description}")
            task_status = "FAILURE"
            result_message = f"Error: {str(e)}"

            # Save failure to database
            if job:
                _save_task_result(job.id, "collector_task", result_message, task_status, core_api)

            raise RuntimeError(e) from e

    # Run post-collection bots
    core_api.run_post_collection_bots(osint_source_id)

    # Save task result to database
    if job:
        _save_task_result(job.id, "collector_task", result_message, task_status, core_api)

    return result_message


def _save_task_result(job_id: str, task_name: str, result: str, status: str, core_api: CoreApi):
    """Save task result to database via Core API.

    Args:
        job_id: RQ job ID
        task_name: Task name/type (e.g., "collector_task")
        result: Task result message
        status: Task status ("SUCCESS" or "FAILURE")
        core_api: CoreApi instance for making API calls
    """
    try:
        task_data = {
            "id": job_id,
            "task": task_name,
            "result": result,
            "status": status,
        }
        response = core_api.api_put("/worker/task-results", task_data)
        if not response:
            logger.warning(f"Failed to save task result for {job_id}")
    except Exception as e:
        logger.error(f"Error saving task result for {job_id}: {e}")


def collector_preview(osint_source_id: str):
    """Preview collection from an OSINT source without saving.

    Args:
        osint_source_id: ID of the OSINT source to preview

    Returns:
        Preview data from the collector
    """
    job = get_current_job()
    collector = Collector()
    source = collector.get_source(osint_source_id)
    collector_impl = collector.get_collector(source)
    formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector_impl.name} {job.id if job else 'preview'}")
    task_description = (
        f"Preview: source '{source.get('name')}' with id {source.get('id')} using collector: '{collector_impl.name}' "
        f"with job id {job.id if job else 'preview'}"
    )

    logger.info(f"Starting preview task: {task_description}")
    with collector_log_fmt(logger, formatter):
        try:
            preview_result = collector_impl.preview_collector(source)
        except NoChangeError as e:
            logger.info(f"No changes detected: {e}")
            return f"'{source.get('name')}': {str(e)}"
        except Exception as e:
            logger.error(f"Collector preview task failed: {task_description}")
            raise RuntimeError(e) from e

    return preview_result


def fetch_single_news_item(parameters: dict[str, Any]):
    job = get_current_job()
    collector = worker.collectors.SimpleWebCollector()
    formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector.name} {job.id if job else 'preview'}")
    task_description = f"Fetching news item wtih {parameters=} and {job.id if job else 'preview'}"
    logger.info(f"Starting collector task: {task_description}")
    core_api = CoreApi()
    result_message = None
    task_status = "SUCCESS"
    with collector_log_fmt(logger, formatter):
        try:
            preview_result = collector.preview_collector(parameters)
        except NoChangeError as e:
            logger.info(f"No changes detected: {e}")
            result_message = f"No changes: {e}"
            if job:
                job.meta["status"] = "NOT_MODIFIED"
                job.meta["message"] = str(e)
                job.save_meta()

            # Save task result to database
            if job:
                _save_task_result(job.id, "collector_task", result_message, task_status, core_api)

            return result_message
        except Exception as e:
            raise RuntimeError(e) from e
    return preview_result
