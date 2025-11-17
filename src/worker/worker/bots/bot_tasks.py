"""RQ Bot Tasks

Functions for executing bots to process news items.
"""
from rq import get_current_job
from datetime import datetime
from croniter import croniter
import redis

import worker.bots
from worker.log import logger
from worker.core_api import CoreApi
from worker.config import Config


def bot_task(bot_id: str, filter: dict | None = None):
    """Execute a bot to process news items.

    Args:
        bot_id: ID of the bot to execute
        filter: Optional filter to limit which items the bot processes

    Returns:
        Result from the bot execution

    Raises:
        ValueError: If bot not found or misconfigured
    """
    job = get_current_job()
    core_api = CoreApi()

    logger.info(f"Starting bot task with job id {job.id if job else 'manual'}")

    # Initialize result tracking
    result_message = "Bot executed successfully"
    task_status = "SUCCESS"
    task_id = job.id if job else f"bot_{bot_id}"

    try:
        if bot_config := core_api.get_bot_config(bot_id):
            result = _execute_by_config(bot_config, filter)

            # Re-schedule if this bot is scheduled (has a refresh interval)
            if not filter and bot_config.get("enabled") and (refresh := bot_config.get("refresh")):
                _reschedule_bot(bot_id, refresh)

            # Save successful result to database
            _save_task_result(task_id, f"bot_{bot_id}", result_message, task_status, core_api)
            return result

        # Bot not found
        result_message = f"Bot with id {bot_id} not found"
        task_status = "FAILURE"
        _save_task_result(task_id, f"bot_{bot_id}", result_message, task_status, core_api)
        raise ValueError(result_message)

    except Exception as e:
        result_message = f"Bot execution failed: {str(e)}"
        task_status = "FAILURE"
        _save_task_result(task_id, f"bot_{bot_id}", result_message, task_status, core_api)
        raise


def _execute_by_config(bot_config: dict, filter: dict | None = None):
    """Execute a bot based on its configuration.

    Args:
        bot_config: Bot configuration dictionary
        filter: Optional filter for bot execution

    Returns:
        Result from the bot execution
    """
    bots = {
        "analyst_bot": worker.bots.AnalystBot(),
        "grouping_bot": worker.bots.GroupingBot(),
        "tagging_bot": worker.bots.TaggingBot(),
        "wordlist_bot": worker.bots.WordlistBot(),
        "nlp_bot": worker.bots.NLPBot(),
        "story_bot": worker.bots.StoryBot(),
        "ioc_bot": worker.bots.IOCBot(),
        "summary_bot": worker.bots.SummaryBot(),
        "sentiment_analysis_bot": worker.bots.SentimentAnalysisBot(),
        "cybersec_classifier_bot": worker.bots.CyberSecClassifierBot(),
    }

    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")

    bot = bots.get(bot_type)
    if not bot:
        raise ValueError(f"Bot type '{bot_type}' not implemented")

    bot_params = bot_config.get("parameters")
    if not bot_params:
        raise ValueError("Bot has no parameters")

    if filter:
        bot_params["filter"] = filter

    return bot.execute(bot_params)

def _reschedule_bot(bot_id: str, cron_expr: str):
    """Re-schedule the bot job for next run.
    
    Fetches the latest configuration from Core API to avoid race conditions
    where configuration is updated while a job is running.

    Args:
        bot_id: ID of the bot
        cron_expr: Fallback cron expression (not used, fresh schedule fetched from Core)
    """
    try:
        from rq import Queue
        from datetime import timezone

        # Connect to Redis
        redis_conn = redis.Redis.from_url(Config.REDIS_URL, password=Config.REDIS_PASSWORD, decode_responses=False)
        queue = Queue("bots", connection=redis_conn)

        # Fetch latest bot configuration from Core API
        core_api = CoreApi()
        bot_config = core_api.get_bot_config(bot_id)
        if not bot_config:
            logger.error(f"Failed to reschedule: bot {bot_id} not found")
            return
        
        # Use fresh schedule from database to avoid race conditions
        # If configuration was updated during job execution, we use the new schedule
        fresh_schedule = bot_config.get("refresh")
        if not fresh_schedule:
            logger.warning(f"Bot {bot_id} has no schedule, skipping reschedule")
            return
        
        # Verify bot is still enabled before rescheduling
        if not bot_config.get("enabled"):
            logger.info(f"Bot {bot_id} is disabled, skipping reschedule")
            return

        # Calculate next run time from fresh cron expression using UTC
        now_utc = datetime.now(timezone.utc)
        cron = croniter(fresh_schedule, now_utc)
        next_run = cron.get_next(datetime)

        # Schedule the task
        task_id = f"bot_{bot_id}"
        queue.enqueue_at(
            next_run,
            "worker.bots.bot_tasks.bot_task",
            bot_id,
            job_id=task_id
        )
        logger.debug(f"Rescheduled bot {bot_id} for {next_run} with schedule {fresh_schedule}")
    except Exception as e:
        logger.error(f"Failed to reschedule bot {bot_id}: {e}")


def _save_task_result(job_id: str, task_name: str, result: str, status: str, core_api):
    """Save task result to database via Core API.

    Args:
        job_id: RQ job ID
        task_name: Task identifier (e.g., 'bot_123')
        result: Result message
        status: Task status ('SUCCESS' or 'FAILURE')
        core_api: CoreApi instance for making API calls
    """
    try:
        task_data = {
            "id": job_id,
            "task": task_name,
            "result": result,
            "status": status
        }
        response = core_api.api_put("/worker/task-results", task_data)
        if response:
            logger.debug(f"Saved task result for {task_name}: {status}")
    except Exception as e:
        logger.error(f"Failed to save task result for {task_name}: {e}")

