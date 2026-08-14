"""RQ Collector Tasks

Functions for collecting news from OSINT sources.
"""

from contextlib import contextmanager
from typing import Any

from rq import get_current_job

import worker.collectors
from worker.collectors.base_collector import BaseCollector, NoChangeError
from worker.collectors.rss_collector import EmptyRSSFeedError
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.log import TaranisLogFormatter, TaranisLogger, logger


RSS_EMPTY_FEED_FAILURE_ATTEMPTS = 3


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


def _persist_and_return_result(
    job,
    core_api: CoreApi,
    result_message: str,
    *,
    worker_id: str | None = None,
    worker_type: str | None = None,
    meta_status: str | None = None,
    reason: str | None = None,
    data: Any = None,
) -> str:
    if not job:
        return result_message

    persisted_status = meta_status or "SUCCESS"

    if meta_status is not None:
        job.meta["status"] = meta_status
        job.meta["message"] = result_message
        job.save_meta()

    core_api.save_task_result(
        job.id,
        "collector_task",
        persisted_status,
        worker_id=worker_id,
        worker_type=worker_type,
        result=build_failure_task_result(
            result_message,
            reason=reason,
            data=data,
        ),
    )
    return result_message


def _next_empty_feed_attempt(source: dict[str, Any]) -> int:
    status = source.get("status")
    if not isinstance(status, dict):
        return 1

    result = status.get("result")
    if not isinstance(result, dict) or result.get("reason") != "rss_feed_empty":
        return 1

    data = result.get("data")
    previous_attempt = data.get("empty_collection_attempts") if isinstance(data, dict) else None
    if not isinstance(previous_attempt, int) or previous_attempt < 1:
        return 1
    return min(previous_attempt + 1, RSS_EMPTY_FEED_FAILURE_ATTEMPTS)


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
        result_message = f"Error: {exc}"
        logger.error(result_message)
        return _persist_and_return_result(
            job,
            core_api,
            result_message,
            worker_id=osint_source_id,
            worker_type="collector_task",
            meta_status="FAILURE",
            reason="source_not_found",
            data={"source_id": osint_source_id, "manual": manual},
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
        except EmptyRSSFeedError as e:
            previous_status = source.get("status")
            if isinstance(previous_status, dict) and previous_status.get("last_success"):
                result_message = f"No new items: RSS feed {e.feed_url} returned no news items after an earlier successful collection"
                logger.info(result_message)
                return _persist_and_return_result(
                    job,
                    core_api,
                    result_message,
                    worker_id=osint_source_id,
                    worker_type=worker_type,
                    meta_status="NOT_MODIFIED",
                    reason="collector_not_modified",
                    data={"source_id": osint_source_id, "manual": manual},
                )

            attempt = _next_empty_feed_attempt(source)
            is_failure = attempt >= RSS_EMPTY_FEED_FAILURE_ATTEMPTS
            if is_failure:
                result_message = (
                    f"Error: RSS feed {e.feed_url} returned no news items after {RSS_EMPTY_FEED_FAILURE_ATTEMPTS} collection attempts"
                )
                logger.error(result_message)
            else:
                result_message = (
                    f"RSS feed {e.feed_url} returned no news items on collection attempt "
                    f"{attempt} of {RSS_EMPTY_FEED_FAILURE_ATTEMPTS}; source remains PENDING"
                )
                logger.warning(result_message)

            _persist_and_return_result(
                job,
                core_api,
                result_message,
                worker_id=osint_source_id,
                worker_type=worker_type,
                meta_status="FAILURE" if is_failure else "PENDING",
                reason="rss_feed_empty",
                data={
                    "source_id": osint_source_id,
                    "manual": manual,
                    "empty_collection_attempts": attempt,
                    "failure_threshold": RSS_EMPTY_FEED_FAILURE_ATTEMPTS,
                },
            )
            if is_failure:
                raise RuntimeError(result_message) from e
            return result_message
        except NoChangeError as e:
            logger.info(f"No changes detected: {e}")
            result_message = f"No changes: {e}"
            return _persist_and_return_result(
                job,
                core_api,
                result_message,
                worker_id=osint_source_id,
                worker_type=worker_type,
                meta_status="NOT_MODIFIED",
                reason="collector_not_modified",
                data={"source_id": osint_source_id, "manual": manual},
            )
        except Exception as e:
            logger.error(f"Collector task failed: {task_description}")
            task_status = "FAILURE"
            result_message = f"Error: {e!s}"

            # Save failure to database
            if job:
                core_api.save_task_result(
                    job.id,
                    "collector_task",
                    task_status,
                    worker_id=osint_source_id,
                    worker_type=worker_type,
                    result=build_failure_task_result(
                        result_message,
                        reason="collection_failed",
                        data={"source_id": osint_source_id, "manual": manual},
                    ),
                )

            raise RuntimeError(e) from e

    # Run post-collection bots
    core_api.run_post_collection_bots(osint_source_id)

    # Save task result to database
    if job:
        core_api.save_task_result(
            job.id,
            "collector_task",
            task_status,
            worker_id=osint_source_id,
            worker_type=worker_type,
            result=build_success_task_result(
                default_message=result_message,
                data={"source_id": osint_source_id, "manual": manual},
            ),
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
            if job:
                collector.core_api.save_task_result(
                    job.id,
                    "collector_preview",
                    "FAILURE",
                    result=build_failure_task_result(
                        str(e),
                        reason="preview_failed",
                        data={"source_id": osint_source_id},
                    ),
                )
            raise RuntimeError(e) from e

    if job:
        collector.core_api.save_task_result(
            job.id,
            "collector_preview",
            "PREVIEW",
            result=build_success_task_result(
                default_message=f"Preview for source {osint_source_id} collected",
                data=preview_result,
            ),
        )

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
                    "NOT_MODIFIED",
                    worker_id=worker_id,
                    worker_type=worker_type,
                    result=build_failure_task_result(
                        result_message,
                        reason="collector_not_modified",
                        data={"source_id": worker_id},
                    ),
                )

            return result_message
        except Exception as e:
            if job:
                core_api.save_task_result(
                    job.id,
                    "collector_task",
                    "FAILURE",
                    worker_id=worker_id,
                    worker_type=worker_type,
                    result=build_failure_task_result(
                        str(e),
                        reason="collection_failed",
                        data={"source_id": worker_id},
                    ),
                )
            raise RuntimeError(e) from e
    if job:
        core_api.save_task_result(
            job.id,
            "collector_task",
            "SUCCESS",
            worker_id=worker_id,
            worker_type=worker_type,
            result=build_success_task_result(
                default_message=f"Fetched news item from {worker_id}",
                data=preview_result,
            ),
        )
    return preview_result
