from datetime import timedelta

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.story import Story


DEBOUNCE_MINUTES = 5


def _job_id(story_id: str) -> str:
    return f"misp_auto_update_{story_id.replace('-', '_')}"


def schedule_story_update(story: Story) -> None:
    sync = story.misp_auto_update
    if not sync:
        return

    job_id = _job_id(story.id)
    queue = queue_manager.queue_manager
    queue.cancel_job(job_id)
    if not sync.enabled:
        return

    pending_until = story.utcnow() + timedelta(minutes=DEBOUNCE_MINUTES)
    sync.pending_until = pending_until
    db.session.commit()
    queue.enqueue_at(
        "connectors",
        "connector_task",
        pending_until,
        sync.connector_id,
        [story.id],
        True,
        job_id=job_id,
        meta=queue._build_task_meta("connector_task", user_id=None, worker_id=sync.connector_id, worker_type="misp_connector"),
    )
