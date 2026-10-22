"""Invalidate task views after their database or RQ state has changed."""

from core.log import logger
from core.managers.realtime_publisher import realtime_publisher
from core.service.cache_invalidation import SCOPE_SCHEDULE, cache_invalidation_service


def notify_task_change(*user_ids: str | None) -> None:
    """Publish content-free hints; authenticated view reads remain authoritative."""
    try:
        cache_invalidation_service.invalidate_scope(SCOPE_SCHEDULE)
    except Exception:
        logger.exception("Could not invalidate task view caches")

    try:
        realtime_publisher.scheduler_changed()
        for user_id in dict.fromkeys(user_id for user_id in user_ids if user_id):
            realtime_publisher.task_changed(user_id)
    except Exception:
        logger.exception("Could not publish task view changes")
