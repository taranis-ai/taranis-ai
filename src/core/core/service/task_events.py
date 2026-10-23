"""Publish task-view changes after their database or RQ state has changed."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from core.log import logger
from core.managers.realtime_publisher import realtime_publisher


_pending_changes: ContextVar[set[str | None] | None] = ContextVar("pending_task_changes", default=None)


@contextmanager
def batch_task_changes() -> Iterator[None]:
    """Coalesce committed changes, including those preceding a partial failure."""
    if _pending_changes.get() is not None:
        yield
        return
    pending: set[str | None] = set()
    token = _pending_changes.set(pending)
    try:
        yield
    finally:
        _pending_changes.reset(token)
        if pending:
            notify_task_change(*pending)


def notify_task_change(*user_ids: str | None) -> None:
    """Publish content-free hints; authenticated view reads remain authoritative."""
    if (pending := _pending_changes.get()) is not None:
        pending.update(user_ids or (None,))
        return
    try:
        realtime_publisher.scheduler_changed()
        for user_id in dict.fromkeys(user_id for user_id in user_ids if user_id):
            realtime_publisher.task_changed(user_id)
    except Exception:
        logger.exception("Could not publish task view changes")
