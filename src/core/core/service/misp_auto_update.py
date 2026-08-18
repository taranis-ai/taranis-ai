from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from core.managers import queue_manager
from core.model.story import Story


DEBOUNCE_MINUTES = 5


def _job_id(story_id: str) -> str:
    return f"misp_auto_update_{story_id.replace('-', '_')}"


def cancel_misp_auto_update_job(story_id: str) -> None:
    queue_manager.queue_manager.cancel_job(_job_id(story_id))


def cancel_misp_auto_update_jobs(story_ids: Iterable[str]) -> None:
    for story_id in set(story_ids):
        if story_id:
            cancel_misp_auto_update_job(story_id)


def refresh_misp_auto_update_job(story_id: str) -> None:
    story = Story.get(story_id)
    if story and not story.misp_auto_update:
        return

    job_id = _job_id(story_id)
    queue = queue_manager.queue_manager
    cancel_misp_auto_update_job(story_id)

    if not story or not (sync := story.misp_auto_update) or not sync.enabled:
        return

    scheduled_time = datetime.now(UTC) + timedelta(minutes=DEBOUNCE_MINUTES)
    queue.enqueue_at(
        "connectors",
        "connector_task",
        scheduled_time,
        sync.connector_id,
        [story_id],
        True,
        job_id=job_id,
        meta=queue._build_task_meta("connector_task", user_id=None, worker_id=sync.connector_id, worker_type="misp_connector"),
    )


def refresh_misp_auto_update_jobs(story_ids: Iterable[str]) -> None:
    for story_id in set(story_ids):
        if story_id:
            refresh_misp_auto_update_job(story_id)
