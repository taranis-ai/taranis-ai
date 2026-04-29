"""RQ Collector Tasks

Functions for collecting news from OSINT sources.
"""

from contextlib import contextmanager
from typing import Any

from rq import get_current_job

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
        raise LookupError(f"Source with id {osint_source_id} not found")

    def get_collector(self, source: dict[str, Any]) -> BaseCollector:
        if collector_type := source.get("type"):
            if collector := self.collectors.get(collector_type):
                return collector
            raise ValueError(f"Collector of type {collector_type} not implemented")
        raise ValueError(f"Source {source['id']} has no collector_type")


def _finalize_successful_non_run(
    job,
    core_api: CoreApi,
    result_message: str,
    *,
    worker_id: str | None = None,
    worker_type: str | None = None,
    meta_status: str | None = None,
) -> str:
    if not job:
        return result_message

    if meta_status is not None:
        job.meta["status"] = meta_status
        job.meta["message"] = result_message
        job.save_meta()

    core_api.save_task_result(job.id, "collector_task", result_message, "SUCCESS", worker_id=worker_id, worker_type=worker_type)
    return result_message


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

    try:
        source = collector.get_source(osint_source_id)
    except LookupError as exc:
        result_message = f"Skipped collector task: {exc}"
        logger.warning(result_message)
        return _finalize_successful_non_run(
            job,
            core_api,
            result_message,
            worker_id=osint_source_id,
            worker_type="collector_task",
            meta_status="SKIPPED",
        )

    collector_impl = collector.get_collector(source)
    worker_type = source.get("type") or "collector_task"
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
            return _finalize_successful_non_run(
                job,
                core_api,
                result_message,
                worker_id=osint_source_id,
                worker_type=worker_type,
                meta_status="NOT_MODIFIED",
            )
        except Exception as e:
            logger.error(f"Collector task failed: {task_description}")
            task_status = "FAILURE"
            result_message = f"Error: {str(e)}"

            # Save failure to database
            if job:
                core_api.save_task_result(
                    job.id,
                    "collector_task",
                    result_message,
                    task_status,
                    worker_id=osint_source_id,
                    worker_type=worker_type,
                )

            raise RuntimeError(e) from e

    # Run post-collection bots
    core_api.run_post_collection_bots(osint_source_id)

    # Save task result to database
    if job:
        core_api.save_task_result(
            job.id,
            "collector_task",
            result_message,
            task_status,
            worker_id=osint_source_id,
            worker_type=worker_type,
        )

    return result_message


def collector_preview(osint_source_id: str):
    """Preview collection from an OSINT source without saving.

    Args:
        osint_source_id: ID of the OSINT source to preview

    Returns:
        Preview data from the collector
    """
    job = get_current_job()
    core_api = CoreApi()
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
            preview_result = []
        except Exception as e:
            logger.error(f"Collector preview task failed: {task_description}")
            raise RuntimeError(e) from e

    if job:
        core_api.save_task_result(job.id, "", preview_result, "SUCCESS")

    return preview_result


def fetch_single_news_item(parameters: dict[str, Any]):
    job = get_current_job()
    collector = worker.collectors.SimpleWebCollector()
    worker_type = "simple_web_collector"
    collector_parameters = parameters["parameters"]
    web_url = collector_parameters.get("WEB_URL")
    worker_id = str(web_url or (job.id if job else "preview"))
    formatter = TaranisLogFormatter(logger.module, custom_prefix=f"{collector.name} {job.id if job else 'preview'}")
    task_description = f"Fetching news item with {parameters=} and {job.id if job else 'preview'}"
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
                core_api.save_task_result(
                    job.id,
                    "collector_task",
                    result_message,
                    task_status,
                    worker_id=worker_id,
                    worker_type=worker_type,
                )

            return result_message
        except Exception as e:
            raise RuntimeError(e) from e
    return preview_result
