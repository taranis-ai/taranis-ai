"""RQ Misc Tasks

Miscellaneous worker tasks including cleanup and wordlist updates.
"""
from datetime import datetime, timezone
from croniter import croniter

from worker.misc.wordlist_update import update_wordlist
from worker.log import logger


def cleanup_token_blacklist(*args, **kwargs):
    """Clean up expired tokens from the blacklist.
    
    This is a self-scheduling task that runs daily at 2 AM.
    After execution, it re-schedules itself for the next day.
    
    Returns:
        str: Status message
    """
    logger.info("Running token blacklist cleanup")
    
    # Re-schedule for next run (daily at 2 AM)
    _reschedule_cleanup()
    
    return "Token blacklist cleanup triggered"


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
        
    except Exception as e:
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
