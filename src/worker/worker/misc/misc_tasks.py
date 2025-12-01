"""RQ Misc Tasks

Miscellaneous worker tasks including cleanup and wordlist updates.
"""
from datetime import datetime, timezone
from croniter import croniter
from rq import get_current_job

from worker.core_api import CoreApi
from worker.misc.wordlist_update import update_wordlist
from worker.log import logger


def cleanup_token_blacklist(*args, reschedule: bool = False, **kwargs):
    """Clean up expired tokens from the blacklist.

    When executed by the RQ cron scheduler this task reports completion to
    the Core API, which triggers removal of stale JWTs. Optional self-
    rescheduling is kept for backwards compatibility but disabled by default
    because the cron scheduler handles recurrence.

    Args:
        reschedule: Whether to enqueue the task manually for the next run.

    Returns:
        str: Status message describing the action.
    """
    logger.info("Running token blacklist cleanup")

    if reschedule:
        _reschedule_cleanup()

    message = "Token blacklist cleanup triggered"

    job = get_current_job()
    if job:
        core_api = CoreApi()
        _save_task_result(job.id, "cleanup_token_blacklist", message, "SUCCESS", core_api)

    return message


def _save_task_result(job_id: str, task_name: str, result: str, status: str, core_api: CoreApi):
    """Persist task result to Core via the worker API."""
    try:
        payload = {
            "id": job_id,
            "task": task_name,
            "result": result,
            "status": status,
        }
        response = core_api.api_put("/worker/task-results", payload)
        if not response:
            logger.warning(f"Failed to save task result for {job_id}")
    except Exception as exc:  # pragma: no cover - log and continue
        logger.error(f"Error saving task result for {job_id}: {exc}")


def _reschedule_cleanup():
    """Re-schedule the cleanup task for next run at 2 AM.

    Uses cron expression '0 2 * * *' (daily at 2:00 AM).
    """
    try:
        # Import here to avoid circular dependency
        import redis
        from rq import Queue
        from worker.config import Config

        # Get Redis connection and queue
        redis_conn = redis.from_url(
            Config.REDIS_URL,
            password=Config.REDIS_PASSWORD,
            decode_responses=False,
        )
        queue = Queue("misc", connection=redis_conn)

        # Calculate next run time from cron expression
        cron_expr = "0 2 * * *"  # Daily at 2 AM
        now = datetime.now(timezone.utc)
        cron = croniter(cron_expr, now)
        next_run = cron.get_next(datetime)

        # Schedule the job
        queue.enqueue_at(next_run, cleanup_token_blacklist)
        logger.info(f"Re-scheduled token cleanup for {next_run.isoformat()}")

    except Exception as e:  # pragma: no cover - logging only
        logger.error(f"Failed to reschedule token cleanup: {e}")


def gather_word_list(word_list_id: int):
    """Gather and update a word list.

    Args:
        word_list_id: ID of the word list to update

    Returns:
        Result from wordlist update
    """
    logger.info(f"Gathering word list {word_list_id}")
    return update_wordlist(word_list_id)
